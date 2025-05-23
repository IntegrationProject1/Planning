import os
import json
import mysql.connector
from mysql.connector import Error

class DBConsumer:
    def __init__(self):
        config = {
            'host':     os.getenv('MYSQL_HOST', 'mysql'),
            'user':     os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'event')
        }
        print(f"Initialiseren MySQL connection voor sessions (user={config['user']})...", flush=True)
        try:
            self.conn = mysql.connector.connect(**config)
            self.cursor = self.conn.cursor(dictionary=True)
            print("MySQL-verbinding session_consumer OK", flush=True)
        except Error as e:
            print("Fout bij verbinden met MySQL:", e, flush=True)
            raise

    def get_calendar_id_for_event(self, event_uuid: str) -> str:
        sql = "SELECT calendar_id FROM calendars WHERE uuid = %s"
        self.cursor.execute(sql, (event_uuid,))
        row = self.cursor.fetchone()
        if not row or 'calendar_id' not in row:
            raise RuntimeError(f"Geen calendar gevonden voor event_uuid {event_uuid}")
        return row['calendar_id']

    def insert_session(self, data: dict):
        calendar_id = self.get_calendar_id_for_event(data['event_uuid'])
        params = {
            'uuid':             data['session_uuid'],
            'event_uuid':       data['event_uuid'],
            'calendar_id':      calendar_id,
            'event_id':         None,
            'name':             data['session_name'],
            'description':      data.get('session_description'),
            'start_datetime':   data.get('start_datetime'),
            'end_datetime':     data.get('end_datetime'),
            'location':         data.get('session_location'),
            'event_type':       data.get('session_type'),
            'capacity':         data.get('capacity'),
            'guest_speaker':    json.dumps(data.get('guest_speaker', []))
        }
        sql = """
            INSERT INTO sessions
              (uuid, event_uuid, calendar_id, event_id,
               name, description,
               start_datetime, end_datetime,
               location, event_type,
               capacity, guest_speaker)
            VALUES
              (%(uuid)s, %(event_uuid)s, %(calendar_id)s, %(event_id)s,
               %(name)s, %(description)s,
               %(start_datetime)s, %(end_datetime)s,
               %(location)s, %(event_type)s,
               %(capacity)s, %(guest_speaker)s)
        """
        try:
            self.cursor.execute(sql, params)
        except mysql.connector.errors.IntegrityError as e:
            # Negeer duplicate key bij create_session
            if e.errno == 1062:
                return
            else:
                raise

        # sla geregistreerde gebruikers op in aparte tabel
        users = data.get('registered_users', [])
        if users:
            for email in users:
                try:
                    self.cursor.execute(
                        "INSERT INTO registered_users (session_uuid, email) VALUES (%s, %s)",
                        (data['session_uuid'], email)
                    )
                except mysql.connector.errors.IntegrityError as e:
                    # Negeer duplicate entry in registered_users
                    if e.errno == 1062:
                        continue
                    else:
                        raise
        self.conn.commit()

    def create_session(self,
                       session_uuid: str,
                       event_uuid: str,
                       start_datetime,
                       end_datetime,
                       session_name: str,
                       session_description: str = None,
                       session_location: str = None,
                       session_type: str = None,
                       capacity: int = None,
                       guest_speaker: list = None,
                       registered_users: list = None):
        """
        Alias voor insert_session, zodat handle_create kan blijven werken.
        """
        data = {
            'session_uuid':        session_uuid,
            'event_uuid':          event_uuid,
            'session_name':        session_name,
            'session_description': session_description,
            'start_datetime':      start_datetime,
            'end_datetime':        end_datetime,
            'session_location':    session_location,
            'session_type':        session_type,
            'capacity':            capacity,
            'guest_speaker':       guest_speaker or [],
            'registered_users':    registered_users or []
        }
        return self.insert_session(data)

    def save_google_info(self,
                         session_uuid: str,
                         calendar_id: str,
                         google_event_id: str):
        sql = "UPDATE sessions SET event_id = %s WHERE uuid = %s"
        self.cursor.execute(sql, (google_event_id, session_uuid))
        self.conn.commit()

    def update_session(self, session_uuid: str, changes: dict,
                       guest_speaker: list = None,
                       registered_users: list = None):
        sets = []
        params = {}
        mapping = {
            'session_name':        'name',
            'session_description': 'description',
            'start_datetime':      'start_datetime',
            'end_datetime':        'end_datetime',
            'session_location':    'location',
            'session_type':        'event_type',
            'capacity':            'capacity'
        }
        for col, val in changes.items():
            db_col = mapping.get(col)
            if db_col:
                sets.append(f"{db_col} = %({col})s")
                params[col] = val
        if guest_speaker is not None:
            sets.append("guest_speaker = %(guest_speaker)s")
            params['guest_speaker'] = json.dumps(guest_speaker)
        if not sets and registered_users is None:
            return
        params['session_uuid'] = session_uuid
        if sets:
            sql = f"UPDATE sessions SET {', '.join(sets)} WHERE uuid = %(session_uuid)s"
            self.cursor.execute(sql, params)
        if registered_users is not None:
            self.cursor.execute(
                "DELETE FROM registered_users WHERE session_uuid = %s",
                (session_uuid,)
            )
            for email in registered_users:
                self.cursor.execute(
                    "INSERT INTO registered_users (session_uuid, email) VALUES (%s, %s)",
                    (session_uuid, email)
                )
        self.conn.commit()

    def delete_session(self, session_uuid: str):
        self.cursor.execute(
            "DELETE FROM registered_users WHERE session_uuid = %s",
            (session_uuid,)
        )
        sql = "DELETE FROM sessions WHERE uuid = %s"
        self.cursor.execute(sql, (session_uuid,))
        self.conn.commit()

    def close(self):
        try:
            self.cursor.close()
            self.conn.close()
        except:
            pass
