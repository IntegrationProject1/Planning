import os
import mysql.connector
from datetime import datetime
from typing import Optional, Dict

class DBConsumer:
    def __init__(self):
        cfg = {
            'host': os.getenv('MYSQL_HOST', 'mysql'),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE')
        }
        self.conn = mysql.connector.connect(**cfg)
        self.cursor = self.conn.cursor(dictionary=True)
        self._ensure_tables()
        self.conn.commit()

    def _ensure_tables(self):
        # sessions
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
        # registered_users
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS registered_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_uuid VARCHAR(255),
                email VARCHAR(255),
                FOREIGN KEY (session_uuid) REFERENCES sessions(uuid) ON DELETE CASCADE
            )
        """)

    def _truncate_to_ms(self, dt: datetime) -> datetime:
        # drop microseconds below the millisecond
        return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)

    def create_session(self, *,
                       session_uuid, event_uuid,
                       start_datetime, end_datetime,
                       session_name=None, session_description=None,
                       session_location=None, session_type=None,
                       capacity=None, guest_speaker=None,
                       registered_users=None,
                       calendar_id=None, event_id=None):
        # Normalize guest_speaker to CSV
        gs_csv = None
        if guest_speaker:
            emails = []
            for g in guest_speaker:
                if isinstance(g, str):
                    emails.append(g)
                else:
                    e = g.get('email') if isinstance(g, dict) else None
                    if e:
                        emails.append(e)
            gs_csv = ",".join(emails) if emails else None

        # Truncate datetimes to ms-precision
        if isinstance(start_datetime, datetime):
            start_datetime = self._truncate_to_ms(start_datetime)
        if isinstance(end_datetime, datetime):
            end_datetime = self._truncate_to_ms(end_datetime)

        sql = """
        INSERT INTO `sessions`
          (uuid, event_uuid, calendar_id, event_id, name, description,
           start_datetime, end_datetime, location, event_type, capacity,
           guest_speaker)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          calendar_id=VALUES(calendar_id), event_id=VALUES(event_id),
          name=VALUES(name), description=VALUES(description),
          start_datetime=VALUES(start_datetime), end_datetime=VALUES(end_datetime),
          location=VALUES(location), event_type=VALUES(event_type),
          capacity=VALUES(capacity), guest_speaker=VALUES(guest_speaker);
        """
        params = (
            session_uuid, event_uuid, calendar_id, event_id,
            session_name, session_description,
            start_datetime, end_datetime, session_location,
            session_type, capacity, gs_csv
        )
        self.cursor.execute(sql, params)

        # Registered users in own table
        if registered_users is not None:
            self.cursor.execute(
                "DELETE FROM `registered_users` WHERE session_uuid = %s",
                (session_uuid,)
            )
            for u in registered_users:
                email = u if isinstance(u, str) else u.get('email')
                if email:
                    self.cursor.execute(
                        "INSERT INTO `registered_users` (session_uuid, email) VALUES (%s, %s)",
                        (session_uuid, email)
                    )

        self.conn.commit()

    def update_session(self, session_uuid, changes, guest_speaker=None, registered_users=None):
        # 1) Skip entire update if parent session doesn't exist
        self.cursor.execute(
            "SELECT 1 FROM sessions WHERE uuid = %s LIMIT 1",
            (session_uuid,)
        )
        if not self.cursor.fetchone():
            return

        # 2) Truncate any changed datetimes to ms-precision
        if 'start_datetime' in changes and isinstance(changes['start_datetime'], datetime):
            changes['start_datetime'] = self._truncate_to_ms(changes['start_datetime'])
        if 'end_datetime' in changes and isinstance(changes['end_datetime'], datetime):
            changes['end_datetime'] = self._truncate_to_ms(changes['end_datetime'])

        # Update guest_speaker if provided
        if guest_speaker is not None:
            emails = []
            for g in guest_speaker:
                if isinstance(g, str):
                    emails.append(g)
                else:
                    e = g.get('email') if isinstance(g, dict) else None
                    if e:
                        emails.append(e)
            gs_csv = ",".join(emails) if emails else None
            self.cursor.execute(
                "UPDATE `sessions` SET `guest_speaker` = %s WHERE uuid = %s",
                (gs_csv, session_uuid)
            )

        # Update registered_users if provided
        if registered_users is not None:
            # remove old registrations
            self.cursor.execute(
                "DELETE FROM `registered_users` WHERE session_uuid = %s",
                (session_uuid,)
            )
            # insert new ones
            for u in registered_users:
                email = u if isinstance(u, str) else u.get('email')
                if email:
                    self.cursor.execute(
                        "INSERT INTO `registered_users` (session_uuid, email) VALUES (%s, %s)",
                        (session_uuid, email)
                    )

        # Update other simple fields
        set_parts, params = [], []
        mapping = {
            'session_name': 'name',
            'session_description': 'description',
            'start_datetime': 'start_datetime',
            'end_datetime': 'end_datetime',
            'session_location': 'location',
            'session_type': 'event_type',
            'capacity': 'capacity',
        }
        for k, v in changes.items():
            col = mapping.get(k)
            if col:
                set_parts.append(f"`{col}` = %s")
                params.append(v)
        if set_parts:
            params.append(session_uuid)
            sql = f"UPDATE `sessions` SET {','.join(set_parts)} WHERE uuid = %s"
            self.cursor.execute(sql, tuple(params))

        self.conn.commit()

    def delete_session(self, session_uuid):
        self.cursor.execute("DELETE FROM `sessions` WHERE uuid = %s", (session_uuid,))
        self.conn.commit()

    def get_calendar_id_for_event(self, event_uuid):
        self.cursor.execute(
            "SELECT calendar_id FROM `sessions` WHERE event_uuid = %s LIMIT 1",
            (event_uuid,)
        )
        row = self.cursor.fetchone()
        return row['calendar_id'] if row else None

    def get_event_id(self, session_uuid):
        self.cursor.execute(
            "SELECT event_id FROM `sessions` WHERE uuid = %s LIMIT 1",
            (session_uuid,)
        )
        row = self.cursor.fetchone()
        return row['event_id'] if row else None

    def save_google_info(self, session_uuid: str, google_calendar_id: str, google_event_id: str) -> None:
        self.cursor.execute(
            "UPDATE `sessions` SET calendar_id = %s, event_id = %s, last_updated = CURRENT_TIMESTAMP WHERE uuid = %s",
            (google_calendar_id, google_event_id, session_uuid)
        )
        self.conn.commit()

    def get_google_info_for_session(self, session_uuid: str) -> Optional[Dict[str, str]]:
        self.cursor.execute(
            "SELECT calendar_id, event_id FROM `sessions` WHERE uuid = %s",
            (session_uuid,)
        )
        row = self.cursor.fetchone()
        if row:
            return {
                'google_calendar_id': row['calendar_id'],
                'google_event_id':    row['event_id']
            }
        return None

    def get_full_session(self, session_uuid: str) -> Dict:
        self.cursor.execute(
            "SELECT uuid, event_type, capacity, description, guest_speaker FROM sessions WHERE uuid = %s",
            (session_uuid,)
        )
        row = self.cursor.fetchone() or {}

        self.cursor.execute(
            "SELECT email FROM registered_users WHERE session_uuid = %s",
            (session_uuid,)
        )
        users = [r['email'] for r in self.cursor.fetchall()]

        gs_csv = row.get('guest_speaker') or ""
        gs_list = [e for e in gs_csv.split(',') if e]

        return {
            'uuid':          row.get('uuid'),
            'guest_speaker': gs_list,
            'session_type':  row.get('event_type'),
            'capacity':      row.get('capacity'),
            'description':   row.get('description'),
            'gasten':        users
        }

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
