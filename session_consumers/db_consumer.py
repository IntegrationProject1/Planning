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
            'session_uuid':        data['session_uuid'],
            'event_uuid':          data['event_uuid'],
            'calendar_id':         calendar_id,
            'event_id':            None,
            'session_name':        data['session_name'],
            'session_description': data.get('session_description'),
            'start_datetime':      data.get('start_datetime'),
            'end_datetime':        data.get('end_datetime'),
            'session_location':    data.get('session_location'),
            'session_type':        data.get('session_type'),
            'capacity':            data.get('capacity'),
            'guest_speaker':       json.dumps(data.get('guest_speaker', [])),
            'registered_users':    json.dumps(data.get('registered_users', []))
        }
        sql = """
            INSERT INTO sessions
              (session_uuid, event_uuid, calendar_id, event_id,
               session_name, session_description,
               start_datetime, end_datetime,
               session_location, session_type,
               capacity, guest_speaker, registered_users)
            VALUES
              (%(session_uuid)s, %(event_uuid)s, %(calendar_id)s, %(event_id)s,
               %(session_name)s, %(session_description)s,
               %(start_datetime)s, %(end_datetime)s,
               %(session_location)s, %(session_type)s,
               %(capacity)s, %(guest_speaker)s, %(registered_users)s)
        """
        self.cursor.execute(sql, params)
        self.conn.commit()

    def update_google_event_id(self, session_uuid: str, google_event_id: str):
        sql = "UPDATE sessions SET event_id = %s WHERE session_uuid = %s"
        self.cursor.execute(sql, (google_event_id, session_uuid))
        self.conn.commit()

    def update_session(self, session_uuid: str, changes: dict,
                       guest_speaker: list = None,
                       registered_users: list = None):
        sets = []
        params = {}
        for col, val in changes.items():
            db_col = {
                'session_name':        'session_name',
                'session_description': 'session_description',
                'start_datetime':      'start_datetime',
                'end_datetime':        'end_datetime',
                'session_location':    'session_location',
                'session_type':        'session_type',
                'capacity':            'capacity'
            }.get(col)
            if db_col:
                sets.append(f"{db_col} = %({col})s")
                params[col] = val
        if guest_speaker is not None:
            sets.append("guest_speaker = %(guest_speaker)s")
            params['guest_speaker'] = json.dumps(guest_speaker)
        if registered_users is not None:
            sets.append("registered_users = %(registered_users)s")
            params['registered_users'] = json.dumps(registered_users)
        if not sets:
            return
        params['session_uuid'] = session_uuid
        sql = f"UPDATE sessions SET {', '.join(sets)} WHERE session_uuid = %(session_uuid)s"
        self.cursor.execute(sql, params)
        self.conn.commit()

    def delete_session(self, session_uuid: str):
        sql = "DELETE FROM sessions WHERE session_uuid = %s"
        self.cursor.execute(sql, (session_uuid,))
        self.conn.commit()

    def close(self):
        try:
            self.cursor.close()
            self.conn.close()
        except:
            pass
