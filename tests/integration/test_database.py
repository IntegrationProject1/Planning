import mysql.connector
import pytest
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "user": "test_user",
    "password": "test_pw",
    "database": "test_db"
}

UUID = "test-uuid"

@pytest.fixture(scope="module")
def db_conn():
    conn = mysql.connector.connect(**DB_CONFIG)
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