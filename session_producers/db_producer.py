from session_producers.xml_generator import (
    build_create_session_xml,
    build_update_session_xml,
    build_delete_session_xml
)
from datetime import datetime, timezone
from dateutil import parser as dateparser
from lxml import etree
import json
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

class DBClient:
    def __init__(self, config, queue):
        import mysql.connector
        self.conn = mysql.connector.connect(**config)
        self.cursor = self.conn.cursor()
        self.queue = queue
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                uuid VARCHAR(255) PRIMARY KEY,
                event_uuid VARCHAR(255),
                calendar_id VARCHAR(255),
                event_id VARCHAR(255),
                name VARCHAR(255),
                description TEXT,
                start_datetime DATETIME(3),
                end_datetime DATETIME(3),
                location VARCHAR(255),
                organizer VARCHAR(255),
                event_type VARCHAR(255),
                capacity INT,
                guest_speaker VARCHAR(255),
                last_updated DATETIME
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS registered_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_uuid VARCHAR(255),
                email VARCHAR(255),
                FOREIGN KEY (session_uuid) REFERENCES sessions(uuid) ON DELETE CASCADE
            )
        """)

    def _format_uuid(self, value):
        try:
            dt = dateparser.parse(value) if not isinstance(value, datetime) else value
            return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
        except Exception as e:
            print(f"⚠️ Kan UUID niet formatteren: {e}", flush=True)
            return str(value)

    def get_by_uuid(self, uuid):
        uuid = self._format_uuid(uuid)
        self.cursor.execute("SELECT * FROM sessions WHERE uuid = %s", (uuid,))
        row = self.cursor.fetchone()
        if not row:
            return None
        col_names = [desc[0] for desc in self.cursor.description]
        return dict(zip(col_names, row))

    def get_registered_users(self, uuid):
        self.cursor.execute("SELECT email FROM registered_users WHERE session_uuid = %s", (uuid,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_event_uuid_from_db(self, calendar_id):
        try:
            self.cursor.execute("SELECT uuid FROM calendars WHERE calendar_id = %s", (calendar_id,))
            row = self.cursor.fetchone()
            if row:
                return row[0]
            else:
                print(f"⚠️ Geen event_uuid gevonden voor calendar_id: {calendar_id}", flush=True)
                return ""
        except Exception as e:
            print(f"❌ Fout bij ophalen event_uuid uit DB: {e}", flush=True)
            return ""

    def resolve_calendar_id_from_event(self, event_id):
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        SERVICE_ACCOUNT_FILE = 'credentials.json'

        try:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            ).with_subject("contact@youmnimalha.be")

            service = build('calendar', 'v3', credentials=creds)
            calendar_list = service.calendarList().list().execute().get("items", [])

            for calendar in calendar_list:
                cal_id = calendar.get("id")
                try:
                    event = service.events().get(calendarId=cal_id, eventId=event_id).execute()
                    if event and event.get("id") == event_id:
                        print(f"📘 Event gevonden in kalender: {cal_id}", flush=True)
                        return cal_id
                except Exception:
                    continue  # Event bestaat niet in deze kalender

            print(f"⚠️ Geen kalender gevonden die event bevat: {event_id}", flush=True)
            return ""

        except Exception as e:
            print(f"❌ Fout bij zoeken naar kalender voor event: {e}", flush=True)
            return ""

    def validate_xml(self, xml_str: str, xsd_filename: str) -> bool:
        try:
            with open(os.path.join("xsd", xsd_filename), 'rb') as f:
                schema_doc = etree.parse(f)
                schema = etree.XMLSchema(schema_doc)
                doc = etree.fromstring(xml_str.encode("utf-8"))
                return schema.validate(doc)
        except Exception as e:
            print(f"XML-validatie fout: {e}", flush=True)
            return False

    def insert(self, data: dict):
        db_data = data.copy()
        db_data['uuid'] = self._format_uuid(db_data['uuid'])
        db_data.pop("registered_users", None)

        self.cursor.execute("""
            INSERT INTO sessions (
                uuid, event_uuid, calendar_id, event_id, name, description, start_datetime, end_datetime,
                location, organizer, event_type, capacity, guest_speaker, last_updated
            ) VALUES (
                %(uuid)s, %(event_uuid)s, %(calendar_id)s, %(event_id)s, %(name)s, %(description)s,
                %(start_datetime)s, %(end_datetime)s, %(location)s, %(organizer)s,
                %(event_type)s, %(capacity)s, %(guest_speaker)s, NOW()
            )
        """, db_data)

        self.insert_registered_users(data["uuid"], data.get("registered_users", []))

        xml = build_create_session_xml(data)
        if self.validate_xml(xml, "create_session.xsd"):
            self.queue.send(["crm.session.create"], xml)
        else:
            print("Ongeldige XML, niet verzonden", flush=True)
        self.conn.commit()

    def update(self, data: dict, changed_fields: dict):
        data_copy = data.copy()
        data_copy['uuid'] = self._format_uuid(data_copy['uuid'])
        data_copy.pop("registered_users", None)

        include_users = "registered_users" in changed_fields

        self.cursor.execute("""
            UPDATE sessions SET
                event_uuid=%(event_uuid)s,
                calendar_id=%(calendar_id)s,
                event_id=%(event_id)s,
                name=%(name)s,
                description=%(description)s,
                start_datetime=%(start_datetime)s,
                end_datetime=%(end_datetime)s,
                location=%(location)s,
                organizer=%(organizer)s,
                event_type=%(event_type)s,
                capacity=%(capacity)s,
                guest_speaker=%(guest_speaker)s,
                last_updated=NOW()
            WHERE uuid=%(uuid)s
        """, data_copy)

        if include_users:
            self.cursor.execute("DELETE FROM registered_users WHERE session_uuid = %s", (data["uuid"],))
            self.insert_registered_users(data["uuid"], data.get("registered_users", []))

        registered_users = data.get("registered_users", []) if include_users else []
        xml = build_update_session_xml(data["uuid"], changed_fields, registered_users)
        if self.validate_xml(xml, "update_session.xsd"):
            self.queue.send(["crm.session.update"], xml)
        else:
            print("Ongeldige XML, niet verzonden", flush=True)
        self.conn.commit()

    def delete(self, uuid):
        uuid = self._format_uuid(uuid)
        self.cursor.execute("DELETE FROM sessions WHERE uuid = %s", (uuid,))
        xml = build_delete_session_xml(uuid)
        if self.validate_xml(xml, "delete_session.xsd"):
            self.queue.send(["crm.session.delete"], xml)
        else:
            print("Ongeldige XML, niet verzonden", flush=True)
        self.conn.commit()

    def insert_registered_users(self, uuid, users):
        for email in users:
            self.cursor.execute(
                "INSERT INTO registered_users (session_uuid, email) VALUES (%s, %s)",
                (uuid, email)
            )

    def process(self, data):
        description_raw = data.get("description")
        try:
            parsed_description = json.loads(description_raw) if description_raw else {}
        except json.JSONDecodeError:
            return "Ongeldige JSON in omschrijving", 400

        uuid = parsed_description.get("uuid")
        event_id = data.get("eventId")
        calendar_id = self.resolve_calendar_id_from_event(event_id)
        event_uuid = self.get_event_uuid_from_db(calendar_id)

        if not uuid:
            return "UUID ontbreekt in omschrijving", 400

        if data.get("status") == "cancelled":
            self.delete(uuid)
            return "Deleted", 200

        parsed = self.parse_event_data(data, uuid, event_uuid, parsed_description)
        parsed["calendar_id"] = calendar_id
        parsed["event_id"] = event_id
        existing = self.get_by_uuid(uuid)
        parsed["registered_users"] = parsed.get("registered_users", [])

        if not existing:
            self.insert(parsed)
            return "Created", 201

        existing["registered_users"] = self.get_registered_users(uuid)
        changes = self.detect_changes(existing, parsed)
        if changes:
            self.update(parsed, changes)
            return "Updated", 200

        return "No change", 200

    def parse_event_data(self, event, uuid, event_uuid, desc):
        start_raw = event.get("start", {}).get("dateTime")
        end_raw = event.get("end", {}).get("dateTime")
        start = dateparser.parse(start_raw).replace(tzinfo=None) if start_raw else None
        end = dateparser.parse(end_raw).replace(tzinfo=None) if end_raw else None

        guestspeaker = desc.get("guestspeaker")
        if isinstance(guestspeaker, list):
            guestspeaker = guestspeaker[0] if guestspeaker else None

        attendees = event.get("attendees", [])
        attendee_emails = [a.get("email") for a in attendees if "email" in a]
        registered_users = desc.get("registered_users", [])
        if not isinstance(registered_users, list):
            registered_users = []

        all_guests = list(set(attendee_emails + registered_users))

        return {
            "uuid": uuid,
            "event_uuid": event_uuid,
            "calendar_id": event.get("calendarId"),
            "event_id": event.get("eventId"),
            "name": event.get("summary"),
            "description": desc.get("description", event.get("description")),
            "start_datetime": start,
            "end_datetime": end,
            "location": event.get("location"),
            "organizer": event.get("organizer", {}).get("email") if isinstance(event.get("organizer"), dict) else None,
            "event_type": desc.get("session_type", "session"),
            "capacity": int(desc.get("capacity", 0)),
            "guest_speaker": guestspeaker,
            "registered_users": all_guests
        }

    def detect_changes(self, old, new):
        diff = {}
        for key in new:
            if key == "registered_users":
                old_list = sorted(old.get("registered_users", []))
                new_list = sorted(new.get("registered_users", []))
                if old_list != new_list:
                    diff[key] = new_list
            elif str(old.get(key)) != str(new.get(key)):
                diff[key] = new[key]
        return diff
