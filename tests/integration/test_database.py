# tests/integration/test_database.py

import mysql.connector
import pytest
import os
from datetime import datetime

DB_CONFIG = {
    "host": os.getenv('MYSQL_HOST', 'localhost'),
    "user": os.getenv('MYSQL_USER', 'test_user'),
    "password": os.getenv('MYSQL_PASSWORD', 'test_pw'),
    "database": os.getenv('MYSQL_DATABASE', 'test_db')
}

UUID = "test-uuid"

@pytest.fixture(scope="module")
def db_conn():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Zorg dat de nodige tabellen bestaan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            uuid VARCHAR(255) PRIMARY KEY,
            event_uuid VARCHAR(255),
            calendar_id VARCHAR(255),
            event_id VARCHAR(255),
            name VARCHAR(255),
            description TEXT,
            start_datetime DATETIME,
            end_datetime DATETIME,
            location VARCHAR(255),
            organizer VARCHAR(255),
            event_type VARCHAR(255),
            capacity INT,
            guest_speaker VARCHAR(255),
            last_updated DATETIME
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registered_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_uuid VARCHAR(255),
            email VARCHAR(255),
            FOREIGN KEY (session_uuid) REFERENCES sessions(uuid) ON DELETE CASCADE
        )
    """)

    conn.commit()
    yield conn
    conn.close()


def test_insert_and_fetch_session(db_conn):
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO sessions (uuid, event_uuid, calendar_id, event_id, name, description,
        start_datetime, end_datetime, location, organizer, event_type, capacity, guest_speaker, last_updated)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, %s, %s, %s, NOW())
    """, (UUID, "event-x", "calendar-x", "eid-x", "Test Sessie", "test desc", "loc", "org", "type", 10, "guest@example.be"))
    db_conn.commit()

    cursor.execute("SELECT * FROM sessions WHERE uuid = %s", (UUID,))
    row = cursor.fetchone()
    assert row is not None
    assert row["name"] == "Test Sessie"


def test_registered_user_insert(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO registered_users (session_uuid, email) VALUES (%s, %s)", (UUID, "student@example.com"))
    db_conn.commit()
    cursor.execute("SELECT email FROM registered_users WHERE session_uuid = %s", (UUID,))
    emails = [r[0] for r in cursor.fetchall()]
    assert "student@example.com" in emails


def test_delete_session(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE uuid = %s", (UUID,))
    db_conn.commit()
    cursor.execute("SELECT * FROM sessions WHERE uuid = %s", (UUID,))
    assert cursor.fetchone() is None
