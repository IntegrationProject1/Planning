from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import os

# Dummy data voor test
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
    "MYSQL_ROOT_PASSWORD": "test-cred!",
    "MYSQL_DATABASE": "test_event_db",
    "MYSQL_USER": "admin",
    "MYSQL_PASSWORD": "test-cred!",
    "MYSQL_HOST": "localhost"
}

@patch.dict(os.environ, ENV_VARS)
@patch("mysql.connector.connect")
@patch("event_producers.db_producer.build_event_xml", return_value="<event/>")
def test_insert(mock_xml, mock_connect):
    from event_producers.db_producer import DBClient
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_queue = MagicMock()

    db = DBClient({}, mock_queue)
    db.insert(dummy_event)

    mock_cursor.execute.assert_called()
    mock_queue.send.assert_called()

@patch.dict(os.environ, ENV_VARS)
@patch("mysql.connector.connect")
@patch("event_producers.db_producer.build_update_xml", return_value="<update/>")
def test_update(mock_xml, mock_connect):
    from event_producers.db_producer import DBClient
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_queue = MagicMock()

    db = DBClient({}, mock_queue)
    db.update(dummy_event, {"name": "Nieuw"})

    mock_cursor.execute.assert_called()
    mock_queue.send.assert_called()

@patch.dict(os.environ, ENV_VARS)
@patch("mysql.connector.connect")
@patch("event_producers.db_producer.build_delete_xml", return_value="<delete/>")
def test_delete(mock_xml, mock_connect):
    from event_producers.db_producer import DBClient
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_queue = MagicMock()

    db = DBClient({}, mock_queue)
    db.delete("1234")

    mock_cursor.execute.assert_called()
    mock_queue.send.assert_called()
