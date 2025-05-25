import mysql.connector
from datetime import datetime, timezone
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
                uuid VARCHAR(255) PRIMARY KEY,
                calendar_id VARCHAR(255),
                name VARCHAR(255),
                created_at DATETIME(6),
                start_datetime DATETIME(3),
                end_datetime DATETIME(3),
                description TEXT,
                capacity INT,
                organizer VARCHAR(255),
                event_type VARCHAR(255),
                location VARCHAR(255),
                last_fetched DATETIME
            )
        """)
        print("Tabel 'calendars' gecontroleerd/aangemaakt", flush=True)

    def _ensure_datetime(self, value, precision='micro'):
        if isinstance(value, datetime):
            dt = value
        else:
            try:
                dt = dateparser.parse(value)
            except Exception as e:
                print(f"⚠️ Kan '{value}' niet omzetten naar datetime: {e}", flush=True)
                return None

        if precision == 'millis':
            return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)
        return dt

    def _format_uuid(self, value):
        """Zet datetime of string om naar ISO-formaat met microseconden en 'Z'."""
        try:
            dt = self._ensure_datetime(value, precision='micro')
            if dt is None:
                return str(value)
            return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
        except Exception as e:
            print(f"⚠️ Kan '{value}' niet formatteren als UUID-string: {e}", flush=True)
            return str(value)

    def get_all_uuids(self):
        print("Ophalen van alle UUID's uit de database...", flush=True)
        self.cursor.execute("SELECT uuid FROM calendars")
        uuids = {row[0] for row in self.cursor.fetchall()}
        print(f"{len(uuids)} UUID's opgehaald", flush=True)
        return uuids

    def get_by_uuid(self, uuid):
        uuid = self._format_uuid(uuid)
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
        data['uuid'] = self._format_uuid(data['uuid'])
        print(f"Invoegen van nieuwe kalender met UUID {data['uuid']}...", flush=True)

        data['created_at'] = self._ensure_datetime(data.get('created_at'), precision='micro')
        data['start_datetime'] = self._ensure_datetime(data.get('start_datetime'), precision='millis')
        data['end_datetime'] = self._ensure_datetime(data.get('end_datetime'), precision='millis')
        data['last_fetched'] = self._ensure_datetime(data.get('last_fetched'))

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
        self.queue.send(["crm.event.create", "kassa.event.create"], xml)
        print(f"Kalender met UUID {data['uuid']} ingevoegd", flush=True)

    def update(self, data: dict, changed_fields: dict):
        data['uuid'] = self._format_uuid(data['uuid'])
        print(f"Updaten van kalender met UUID {data['uuid']}...", flush=True)

        data['created_at'] = self._ensure_datetime(data.get('created_at'), precision='micro')
        data['start_datetime'] = self._ensure_datetime(data.get('start_datetime'), precision='millis')
        data['end_datetime'] = self._ensure_datetime(data.get('end_datetime'), precision='millis')
        data['last_fetched'] = self._ensure_datetime(data.get('last_fetched'))

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

        xml = build_update_xml(data['uuid'], changed_fields)
        print(f"Versturen van 'updated' bericht voor UUID {data['uuid']}...", flush=True)
        self.queue.send(["crm.event.update", "kassa.event.update"], xml)
        print(f"Kalender met UUID {data['uuid']} bijgewerkt", flush=True)

    def delete(self, uuid):
        uuid = self._format_uuid(uuid)
        print(f"Verwijderen van kalender met UUID {uuid}...", flush=True)
        self.cursor.execute("DELETE FROM calendars WHERE uuid = %s", (uuid,))
        xml = build_delete_xml(uuid)
        print(f"Versturen van 'deleted' bericht voor UUID {uuid}...", flush=True)
        self.queue.send(["crm.event.delete", "kassa.event.delete"], xml)
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
