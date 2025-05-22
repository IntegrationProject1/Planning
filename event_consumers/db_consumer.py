import os
import mysql.connector

class DBClient:
    """
    Database client for consumer service.
    Werkt met tabellen `calendars` en `registered_users`.
    """
    def __init__(self):
        config = {
            'host':     os.getenv('MYSQL_HOST', 'mysql'),
            'user':     os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE')
        }
        print("Initialiseren van MySQL-verbinding (consumer)...", flush=True)
        self.conn = mysql.connector.connect(**config)
        self.cursor = self.conn.cursor(dictionary=True)
        print("MySQL-verbinding consumer klaar", flush=True)

        # Zorg dat tabellen bestaan
        self._ensure_tables()
        self.conn.commit()

    def _ensure_tables(self):
        print("Aanmaken van 'calendars' tabel indien nodig...", flush=True)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS `calendars` (
            `uuid` DATETIME PRIMARY KEY,
            `calendar_id` VARCHAR(255),
            `name` VARCHAR(255),
            `created_at` DATETIME,
            `start_datetime` DATETIME,
            `end_datetime` DATETIME,
            `description` TEXT,
            `capacity` INT,
            `organizer` VARCHAR(255),
            `event_type` VARCHAR(255),
            `location` VARCHAR(255),
            `last_fetched` DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Tabel 'calendars' gecontroleerd/aangemaakt", flush=True)

        print("Aanmaken van 'registered_users' tabel indien nodig...", flush=True)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS `registered_users` (
            `event_uuid` DATETIME NOT NULL,
            `user_uuid` VARCHAR(255) NOT NULL,
            PRIMARY KEY (`event_uuid`, `user_uuid`),
            CONSTRAINT `fk_registered_event`
              FOREIGN KEY (`event_uuid`)
              REFERENCES `calendars`(`uuid`)
              ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Tabel 'registered_users' gecontroleerd/aangemaakt", flush=True)

    def insert(self, data: dict):
        """
        Insert of upsert van kalender en bijbehorende registered_users.
        """
        print(f"Invoegen van nieuwe kalender (consumer) met UUID {data.get('uuid')}...", flush=True)
        cal_data = data.copy()
        users = cal_data.pop('registered_users', [])

        # Normalize organizer key
        if 'organisator' in cal_data:
            cal_data['organizer'] = cal_data.pop('organisator')

        # Kalender upsert
        sql_cal = (
            "INSERT INTO `calendars` (`uuid`,`name`,`description`,`start_datetime`,`end_datetime`,`location`,`organizer`,`capacity`,`event_type`) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE "
            "`name`=VALUES(`name`),`description`=VALUES(`description`),"  
            "`start_datetime`=VALUES(`start_datetime`),`end_datetime`=VALUES(`end_datetime`),"  
            "`location`=VALUES(`location`),`organizer`=VALUES(`organizer`),"  
            "`capacity`=VALUES(`capacity`),`event_type`=VALUES(`event_type`);"
        )
        self.cursor.execute(sql_cal, (
            cal_data['uuid'], cal_data['name'], cal_data['description'],
            cal_data['start_datetime'], cal_data['end_datetime'], cal_data['location'],
            cal_data['organizer'], cal_data['capacity'], cal_data['event_type']
        ))

        # Clear oude users
        self.cursor.execute(
            "DELETE FROM `registered_users` WHERE `event_uuid` = %s",
            (cal_data['uuid'],)
        )

        # Insert nieuwe users
        if users:
            print(f"Invoegen van {len(users)} geregistreerde gebruikers...", flush=True)
            ins_sql = "INSERT INTO `registered_users` (`event_uuid`,`user_uuid`) VALUES (%s,%s)"
            for u in users:
                user_uuid = u.get('uuid') if isinstance(u, dict) else u
                self.cursor.execute(ins_sql, (cal_data['uuid'], user_uuid))

    def update(self, uuid, fields: dict):
        """
        Update van kalender-velden en bijhorende users indien opgegeven.
        """
        print(f"Updaten van kalender (consumer) met UUID {uuid}...", flush=True)
        users = None
        if 'registered_users' in fields:
            users = fields.pop('registered_users')

        # Normalize organizer
        if 'organisator' in fields:
            fields['organizer'] = fields.pop('organisator')

        # Kalender update
        set_clauses = []
        params = []
        for key, value in fields.items():
            set_clauses.append(f"`{key}`=%s")
            params.append(value)
        params.append(uuid)
        if set_clauses:
            sql = f"UPDATE `calendars` SET {','.join(set_clauses)} WHERE `uuid`=%s"
            self.cursor.execute(sql, tuple(params))

        # Users vervangen als nodig
        if users is not None:
            self.cursor.execute(
                "DELETE FROM `registered_users` WHERE `event_uuid`=%s",
                (uuid,)
            )
            if users:
                ins_sql = "INSERT INTO `registered_users` (`event_uuid`,`user_uuid`) VALUES (%s,%s)"
                for u in users:
                    user_uuid = u.get('uuid') if isinstance(u, dict) else u
                    self.cursor.execute(ins_sql, (uuid, user_uuid))

    def delete(self, uuid):
        """Verwijdert kalender en cascades naar registered_users."""
        print(f"Verwijderen van kalender (consumer) met UUID {uuid}...", flush=True)
        self.cursor.execute("DELETE FROM `calendars` WHERE `uuid`=%s", (uuid,))

    def commit(self):
        print("Databasewijzigingen consumer vastleggen...", flush=True)
        self.conn.commit()

    def close(self):
        print("Sluiten van MySQL-verbinding (consumer)...", flush=True)
        self.cursor.close()
        self.conn.close()
        print("MySQL consumer gesloten", flush=True)
