import mysql.connector

class DBClient:
    def __init__(self, config: dict):
        print("Connecting to MySQL...", flush=True)
        self.conn = mysql.connector.connect(**config)
        self.cursor = self.conn.cursor()
        self._create_table()
        print("MySQL connected and table ready", flush=True)

    def _create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendars (
                uuid VARCHAR(36) PRIMARY KEY,
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

    def get_by_uuid(self, uuid: str) -> dict:
        self.cursor.execute("SELECT * FROM calendars WHERE uuid = %s", (uuid,))
        row = self.cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in self.cursor.description]
        return dict(zip(cols, row))

    def insert(self, data: dict):
        self.cursor.execute("""
            INSERT INTO calendars (
                uuid, calendar_id, name, created_at, start_datetime, end_datetime,
                description, capacity, organizer, event_type, location, last_fetched
            ) VALUES (
                %(uuid)s, %(calendar_id)s, %(name)s, %(created_at)s,
                %(start_datetime)s, %(end_datetime)s, %(description)s,
                %(capacity)s, %(organizer)s, %(event_type)s, %(location)s,
                %(last_fetched)s
            )
        """, data)

    def update(self, data: dict, changed_fields: dict):
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

    def delete(self, uuid: str):
        self.cursor.execute("DELETE FROM calendars WHERE uuid = %s", (uuid,))

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()