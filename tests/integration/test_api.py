import requests
import json
import pytest

BASE_URL = "http://session_producer:30015"
UUID = "2025-05-22T15:00:00.000000Z"

@pytest.mark.order(1)
def test_create_session():
    payload = {
        "calendarId": "test-calendar",
        "eventId": "evt123",
        "summary": "Docker Deep Dive",
        "description": json.dumps({
            "uuid": UUID,
            "guestspeaker": ["dave@example.be"],
            "session_type": "training",
            "capacity": 30,
            "description": "Intro to containers",
            "registered_users": ["student1@example.com"]
        }),
        "status": "confirmed",
        "start": {"dateTime": "2025-05-22T16:00:00+02:00"},
        "end": {"dateTime": "2025-05-22T17:00:00+02:00"},
        "updated": "2025-05-20T12:30:00Z",
        "attendees": [
            {"email": "student1@example.com"},
            {"email": "student2@example.com"}
        ]
    }
    res = requests.post(f"{BASE_URL}/api/calendar-ping", json=payload)
    assert res.status_code in [200, 201]
    assert res.text in ["Created", "Updated", "No change"]

@pytest.mark.order(2)
def test_update_session():
    payload = {
        "calendarId": "test-calendar",
        "eventId": "evt123",
        "summary": "Docker Deep Dive - Updated",
        "description": json.dumps({
            "uuid": UUID,
            "guestspeaker": ["dave@example.be"],
            "session_type": "workshop",
            "capacity": 25,
            "description": "Updated content",
            "registered_users": ["student1@example.com"]
        }),
        "status": "confirmed",
        "start": {"dateTime": "2025-05-22T16:00:00+02:00"},
        "end": {"dateTime": "2025-05-22T18:00:00+02:00"},
        "updated": "2025-05-21T12:30:00Z",
        "attendees": [
            {"email": "student1@example.com"}
        ]
    }
    res = requests.post(f"{BASE_URL}/api/calendar-ping", json=payload)
    assert res.status_code == 200
    assert res.text == "Updated"

@pytest.mark.order(3)
def test_delete_session():
    payload = {
        "calendarId": "test-calendar",
        "eventId": "evt123",
        "summary": "Docker Deep Dive",
        "description": json.dumps({"uuid": UUID}),
        "status": "cancelled",
        "start": {"dateTime": "2025-05-22T16:00:00+02:00"},
        "end": {"dateTime": "2025-05-22T17:00:00+02:00"},
        "updated": "2025-05-20T12:30:00Z"
    }
    res = requests.post(f"{BASE_URL}/api/calendar-ping", json=payload)
    assert res.status_code == 200
    assert res.text == "Deleted"
