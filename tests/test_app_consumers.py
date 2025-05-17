import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from event_consumers.app import handle_message, QUEUES

@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    monkeypatch.setenv('SHARE_WITH_EMAIL', 'test@example.com')

# Dummy data with datetime uuid
dummy_data = {
    'uuid': datetime(2025, 8, 15, 10, 0),
    'name': 'E',
    'description': 'D',
    'start_datetime': datetime(2025, 8, 15, 9, 0),
    'end_datetime': datetime(2025, 8, 15, 11, 0),
    'location': 'L',
    'organisator': 'org@example.com',
    'capacity': 10,
    'event_type': 'Test',
    'registered_users': [{'uuid': 'alice@example.com'}, {'uuid': 'bob@example.com'}]
}

@pytest.fixture(autouse=True)
def patch_deps(monkeypatch):
    fake_db = MagicMock()
    monkeypatch.setattr('event_consumers.app.DBClient', lambda: fake_db)
    fake_cal = MagicMock()
    fake_cal.create_calendar.return_value = {'id': 'cal1', 'timeCreated': '2025-08-15T10:00:00Z'}
    fake_cal.subscribe_calendar.return_value = None
    fake_cal.share_calendar.return_value = None
    fake_cal.create_event.return_value = {'id': 'evt1'}
    fake_cal.update_event.return_value = None
    fake_cal.delete_calendar.return_value = None
    monkeypatch.setattr('event_consumers.app.CalendarClient', lambda f: fake_cal)

@patch('event_consumers.app.parse_create_event_xml', return_value=dummy_data)
def test_handle_created(mock_parse):
    handle_message(QUEUES[0], b'<CreateEvent/>')
    from event_consumers.app import CalendarClient
    cal = CalendarClient(None)
    cal.create_calendar.assert_called_once()
    cal.subscribe_calendar.assert_called_once()
    cal.create_event.assert_called_once()

@patch('event_consumers.app.parse_update_event_xml', return_value=(dummy_data['uuid'], {'description': 'New'}))
def test_handle_updated(mock_parse):
    handle_message(QUEUES[1], b'<UpdateEvent/>')
    from event_consumers.app import CalendarClient
    cal = CalendarClient(None)
    cal.update_event.assert_called_once()

@patch('event_consumers.app.parse_delete_event_xml', return_value=dummy_data['uuid'])
def test_handle_deleted(mock_parse):
    handle_message(QUEUES[2], b'<DeleteEvent/>')
    from event_consumers.app import CalendarClient
    cal = CalendarClient(None)
    cal.delete_calendar.assert_called_once()