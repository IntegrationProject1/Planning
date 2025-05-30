import os
import mysql.connector
from datetime import datetime

class DBClient:
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

        self._ensure_tables()
        self.conn.commit()

    def _ensure_tables(self):
        print("Aanmaken van 'calendars' tabel indien nodig...", flush=True)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS `calendars` (
            `uuid` VARCHAR(255) PRIMARY KEY,
            `calendar_id` VARCHAR(255),
            `name` VARCHAR(255),
            `created_at` DATETIME(6),
            `start_datetime` DATETIME(3),
            `end_datetime` DATETIME(3),
            `description` TEXT,
            `capacity` INT,
            `organizer` VARCHAR(255),
            `event_type` VARCHAR(255),
            `location` VARCHAR(255),
            `last_fetched` DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Tabel 'calendars' gecontroleerd/aangemaakt", flush=True)

        print("Aanmaken van 'event_users' tabel indien nodig...", flush=True)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS `event_users` (
            `event_uuid` VARCHAR(255) NOT NULL,
            `user_uuid`  VARCHAR(255) NOT NULL,
            PRIMARY KEY (`event_uuid`, `user_uuid`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Tabel 'event_users' gecontroleerd/aangemaakt", flush=True)

    def _truncate_to_ms(self, dt):
        return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)

    def insert(self, data: dict):
        print(f"Invoegen van nieuwe kalender (consumer) met UUID {data.get('uuid')}...", flush=True)
        cal_data = data.copy()
        users = cal_data.pop('registered_users', [])

        if 'organisator' in cal_data:
            cal_data['organizer'] = cal_data.pop('organisator')

        cal_data['uuid'] = str(cal_data['uuid'])

        if isinstance(cal_data.get('start_datetime'), datetime):
            cal_data['start_datetime'] = self._truncate_to_ms(cal_data['start_datetime'])
        if isinstance(cal_data.get('end_datetime'), datetime):
            cal_data['end_datetime']   = self._truncate_to_ms(cal_data['end_datetime'])

        sql_cal = (
            "INSERT INTO `calendars` (`uuid`,`name`,`description`,`start_datetime`,`end_datetime`,`location`,`organizer`,`capacity`,`event_type`,`calendar_id`,`created_at`,`last_fetched`) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE "
            "`name`=VALUES(`name`),`description`=VALUES(`description`),"
            "`start_datetime`=VALUES(`start_datetime`),`end_datetime`=VALUES(`end_datetime`),"
            "`location`=VALUES(`location`),`organizer`=VALUES(`organizer`),"
            "`capacity`=VALUES(`capacity`),`event_type`=VALUES(`event_type`),"
            "`calendar_id`=VALUES(`calendar_id`),`created_at`=VALUES(`created_at`),`last_fetched`=VALUES(`last_fetched`);")
        print(f"DEBUG payload voor insert: {cal_data}", flush=True)
        self.cursor.execute(sql_cal, (
            cal_data['uuid'], cal_data['name'], cal_data['description'],
            cal_data['start_datetime'], cal_data['end_datetime'], cal_data['location'],
            cal_data['organizer'], cal_data['capacity'], cal_data['event_type'],
            cal_data.get('calendar_id'), cal_data.get('created_at'), cal_data.get('last_fetched')
        ))

        self.cursor.execute(
            "DELETE FROM `event_users` WHERE `event_uuid` = %s",
            (cal_data['uuid'],)
        )

        if users:
            print(f"Invoegen van {len(users)} event gebruikers...", flush=True)
            ins_sql = "INSERT INTO `event_users` (`event_uuid`,`user_uuid`) VALUES (%s,%s)"
            for u in users:
                user_uuid = u.get('uuid') if isinstance(u, dict) else u
                self.cursor.execute(ins_sql, (cal_data['uuid'], user_uuid))

    def update(self, uuid, fields: dict):
        print(f"Updaten van kalender (consumer) met UUID {uuid}...", flush=True)
        print(f"[DEBUG] UUID tijdens update: {uuid}")
        print(f"[DEBUG] Fields tijdens update: {fields}")
        users = fields.pop('registered_users', None)

        if 'organisator' in fields:
            fields['organizer'] = fields.pop('organisator')

        if isinstance(fields.get('start_datetime'), datetime):
            fields['start_datetime'] = self._truncate_to_ms(fields['start_datetime'])
        if isinstance(fields.get('end_datetime'), datetime):
            fields['end_datetime']   = self._truncate_to_ms(fields['end_datetime'])

        set_clauses = []
        params = []
        for key, value in fields.items():
            set_clauses.append(f"`{key}`=%s")
            params.append(value)
        params.append(uuid)
        if set_clauses:
            sql = f"UPDATE `calendars` SET {','.join(set_clauses)} WHERE `uuid`=%s"
            self.cursor.execute(sql, tuple(params))

        if users is not None:
            self.cursor.execute("DELETE FROM `event_users` WHERE `event_uuid`=%s", (uuid,))
            if users:
                ins_sql = "INSERT INTO `event_users` (`event_uuid`,`user_uuid`) VALUES (%s,%s)"
                for u in users:
                    user_uuid = u.get('uuid') if isinstance(u, dict) else u
                    self.cursor.execute(ins_sql, (uuid, user_uuid))

    def delete(self, uuid):
        print(f"Verwijderen van kalender (consumer) met UUID {uuid}...", flush=True)
        # verwijder eerst alle gekoppelde gebruikers
        self.cursor.execute(
            "DELETE FROM `event_users` WHERE `event_uuid` = %s",
            (uuid,)
        )
        # en daarna pas de kalender zelf
        self.cursor.execute(
            "DELETE FROM `calendars` WHERE `uuid` = %s",
            (uuid,)
        )

    def commit(self):
        print("Databasewijzigingen consumer vastleggen...", flush=True)
        self.conn.commit()

    def close(self):
        print("Sluiten van MySQL-verbinding (consumer)...", flush=True)
        self.cursor.close()
        self.conn.close()
        print("MySQL consumer gesloten", flush=True)
