# File: event_consumers/db_consumer.py

import os
import mysql.connector

class DBClient:
    """
    Database client for consumer service. Inserts, updates, deletes events
    and their registered users into MySQL.
    """
    def __init__(self):
        # Load DB config from environment
        config = {
            'host': os.getenv('MYSQL_HOST', 'mysql'),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE')
        }
        print("Initialiseren van MySQL-verbinding (consumer)...", flush=True)
        self.conn = mysql.connector.connect(**config)
        # cursor die dicts teruggeeft in plaats van tuples
        self.cursor = self.conn.cursor(dictionary=True)

        print("MySQL-verbinding consumer klaar", flush=True)

    def insert(self, data: dict):
        print(f"Invoegen van nieuwe kalender (consumer) met UUID {data.get('uuid')}...", flush=True)
        # Extract registered users list if present
        users = data.pop('registered_users', [])

        sql = """
        INSERT INTO calendars (
            uuid, name, description,
            start_datetime, end_datetime,
            location, organizer, capacity, event_type
        ) VALUES (
            %(uuid)s, %(name)s, %(description)s,
            %(start_datetime)s, %(end_datetime)s,
            %(location)s, %(organizer)s, %(capacity)s, %(event_type)s
        )
        ON DUPLICATE KEY UPDATE
            name=VALUES(name),
            description=VALUES(description),
            start_datetime=VALUES(start_datetime),
            end_datetime=VALUES(end_datetime),
            location=VALUES(location),
            organizer=VALUES(organizer),
            capacity=VALUES(capacity),
            event_type=VALUES(event_type);
        """
        # Execute main upsert
        self.cursor.execute(sql, data)

        # Sync registered users
        self.cursor.execute(
            "DELETE FROM event_users WHERE event_uuid = %s", (data['uuid'],)
        )
        for user_uuid in users:
            self.cursor.execute(
                "INSERT INTO event_users (event_uuid, user_uuid) VALUES (%s, %s)",
                (data['uuid'], user_uuid)
            )
        print(f"Registered users gesynchroniseerd: {len(users)} entries", flush=True)

    def update(self, uuid: str, fields: dict):
        print(f"Updaten van kalender (consumer) met UUID {uuid}...", flush=True)
        sql_set = []
        params = {}
        for key, value in fields.items():
            sql_set.append(f"{key} = %({key})s")
            params[key] = value
        params['uuid'] = uuid
        sql = f"UPDATE calendars SET {', '.join(sql_set)} WHERE uuid = %(uuid)s"
        self.cursor.execute(sql, params)

    def delete(self, uuid: str):
        print(f"Verwijderen van kalender (consumer) met UUID {uuid}...", flush=True)
        # Delete event (cascades on event_users)
        self.cursor.execute("DELETE FROM calendars WHERE uuid = %s", (uuid,))

    def commit(self):
        print("Databasewijzigingen consumer vastleggen...", flush=True)
        self.conn.commit()

    def close(self):
        print("Sluiten van MySQL-verbinding (consumer)...", flush=True)
        self.cursor.close()
        self.conn.close()
        print("MySQL consumer gesloten", flush=True)
