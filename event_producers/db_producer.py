import mysql.connector
from datetime import datetime
from dateutil import parser as dateparser
from event_producers.xml_generator import (
    build_event_xml,
    build_update_xml,
    build_delete_xml
)

class DBClient:
    def __init__(self, config, queue_client):
        print("Initialiseren van MySQL-verbinding...", flush=True)
        self.conn = mysql.connector.connect(**config)
        self.cursor = self.conn.cursor()
        self.queue = queue_client
        self._create_table()
        print("MySQL-verbinding en tabel succesvol geïnitialiseerd", flush=True)

    def _create_table(self):
        print("Aanmaken van 'calendars' tabel indien nodig...", flush=True)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendars (
                uuid DATETIME PRIMARY KEY,
                calendar_id VARCHAR(255),
                name VARCHAR(255),
                created_at DATETIME,
                start_datetime DATETIME,
                end_datetime DATETIME,
                description TEXT,
                capacity INT,
                organizer VARCHAR(255),
                event_type VARCHAR(255),
                location VARCHAR(255),
                last_fetched DATETIME
            )
        """)
        print("Tabel 'calendars' gecontroleerd/ aangemaakt", flush=True)

    def get_all_uuids(self):
        print("Ophalen van alle UUID's uit de database...", flush=True)
        self.cursor.execute("SELECT uuid FROM calendars")
        uuids = {row[0] for row in self.cursor.fetchall()}
        print(f"{len(uuids)} UUID's opgehaald", flush=True)
        return uuids

    def get_by_uuid(self, uuid):
        print(f"Ophalen van kalender met UUID {uuid}...", flush=True)
        self.cursor.execute("SELECT * FROM calendars WHERE uuid = %s", (uuid,))
        row = self.cursor.fetchone()
        if not row:
            print(f"Geen kalender gevonden voor UUID {uuid}", flush=True)
            return None
        col_names = [desc[0] for desc in self.cursor.description]
        result = dict(zip(col_names, row))
        print(f"Kalender gevonden voor UUID {uuid}", flush=True)
        return result

    def insert(self, data: dict):
        print(f"Invoegen van nieuwe kalender met UUID {data['uuid']}...", flush=True)
        self.cursor.execute("""
            INSERT INTO calendars (
                uuid, calendar_id, name, created_at, start_datetime, end_datetime,
                description, capacity, organizer, event_type, location, last_fetched
            ) VALUES (%(uuid)s, %(calendar_id)s, %(name)s, %(created_at)s,
                      %(start_datetime)s, %(end_datetime)s, %(description)s,
                      %(capacity)s, %(organizer)s, %(event_type)s, %(location)s,
                      %(last_fetched)s)
        """, data)
        xml = build_event_xml(data)
        print(f"Versturen van 'created' bericht voor UUID {data['uuid']}...", flush=True)
        self.queue.send(["crm.event.created", "kassa.event.created"], xml)
        print(f"Kalender met UUID {data['uuid']} ingevoegd", flush=True)

    def update(self, data: dict, changed_fields: dict):
        print(f"Updaten van kalender met UUID {data['uuid']}...", flush=True)
        self.cursor.execute("""
            UPDATE calendars SET
                calendar_id=%(calendar_id)s,
                name=%(name)s,
                created_at=%(created_at)s,
                start_datetime=%(start_datetime)s,
                end_datetime=%(end_datetime)s,
                description=%(description)s,
                capacity=%(capacity)s,
                organizer=%(organizer)s,
                event_type=%(event_type)s,
                location=%(location)s,
                last_fetched=%(last_fetched)s
            WHERE uuid=%(uuid)s
        """, data)

        event_datetime = data["uuid"]
        if isinstance(event_datetime, str):
            event_datetime = dateparser.parse(event_datetime)

        xml = build_update_xml(event_datetime, changed_fields)

        print(f"Versturen van 'updated' bericht voor UUID {data['uuid']}...", flush=True)
        self.queue.send(["crm.event.updated", "kassa.event.updated"], xml)
        print(f"Kalender met UUID {data['uuid']} bijgewerkt", flush=True)

    def delete(self, uuid):
        print(f"Verwijderen van kalender met UUID {uuid}...", flush=True)
        self.cursor.execute("DELETE FROM calendars WHERE uuid = %s", (uuid,))
        xml = build_delete_xml(uuid)
        print(f"Versturen van 'deleted' bericht voor UUID {uuid}...", flush=True)
        self.queue.send(["crm.event.deleted", "kassa.event.deleted"], xml)
        print(f"Kalender met UUID {uuid} verwijderd", flush=True)

    def commit(self):
        print("Databasewijzigingen vastleggen...", flush=True)
        self.conn.commit()
        print("Databasewijzigingen succesvol vastgelegd", flush=True)

    def close(self):
        print("Sluiten van databaseverbinding...", flush=True)
        self.cursor.close()
        self.conn.close()
        print("Databaseverbinding gesloten", flush=True)