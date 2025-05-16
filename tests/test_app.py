from unittest.mock import patch
from datetime import datetime, timezone
import os

dummy_event = {
    'uuid': '1234',
    'calendar_id': 'abc',
    'name': 'Test Event',
    'created_at': datetime.now(timezone.utc),
    'start_datetime': datetime(2024, 5, 10, 10, 0),
    'end_datetime': datetime(2024, 5, 10, 12, 0),
    'description': 'Beschrijving',
    'capacity': 10,
    'organizer': 'Organisator',
    'event_type': 'Workshop',
    'location': 'Lokaal 1',
    'last_fetched': datetime.now(timezone.utc)
}

ENV_VARS = {
    "MYSQL_HOST": "localhost",
    "MYSQL_USER": "test_user",
    "MYSQL_PASSWORD": "test_pass",
    "MYSQL_DATABASE": "test_db",
    "MYSQL_ROOT_PASSWORD": "test_root"
}

@patch.dict(os.environ, ENV_VARS)
def test_parse_date_valid():
    from event_producers.app import parse_date
    date_str = "2024-05-10T10:00:00"
    assert isinstance(parse_date(date_str), datetime)

@patch.dict(os.environ, ENV_VARS)
def test_parse_date_invalid():
    from event_producers.app import parse_date
    assert parse_date("geen datum") is None

@patch.dict(os.environ, ENV_VARS)
def test_detect_changes_detects_change():
    from event_producers.app import detect_changes
    nieuw = dummy_event.copy()
    nieuw['capacity'] = 20
    resultaat = detect_changes(dummy_event, nieuw)
    assert 'capacity' in resultaat
    assert resultaat['capacity'] == 20

@patch.dict(os.environ, ENV_VARS)
def test_detect_changes_geen_wijziging():
    from event_producers.app import detect_changes
    assert detect_changes(dummy_event, dummy_event.copy()) == {}
