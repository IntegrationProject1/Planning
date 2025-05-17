import pytest
from datetime import datetime
from unittest.mock import MagicMock
from event_consumers.db_consumer import DBClient

@pytest.fixture
def mock_connect(monkeypatch):
    fake_conn = MagicMock()
    fake_cursor = MagicMock()
    fake_conn.cursor.return_value = fake_cursor
    monkeypatch.setattr('mysql.connector.connect', lambda **kwargs: fake_conn)
    return fake_conn, fake_cursor


def test_db_insert(mock_connect):
    conn, cursor = mock_connect
    db = DBClient()
    data = {
        'uuid': datetime(2025, 8, 15, 10, 0),
        'name': 'N',
        'description': 'D',
        'start_datetime': None,
        'end_datetime': None
    }
    db.insert(data)
    assert cursor.execute.called


def test_db_update(mock_connect):
    conn, cursor = mock_connect
    db = DBClient()
    db.update(
        datetime(2025, 8, 15, 10, 0),
        {'name': 'New'}
    )
    sql, params = cursor.execute.call_args[0]
    assert 'UPDATE' in sql
    assert params['name'] == 'New'
    assert params['uuid'] == datetime(2025, 8, 15, 10, 0)


def test_db_delete(mock_connect):
    conn, cursor = mock_connect
    db = DBClient()
    db.delete(datetime(2025, 8, 15, 10, 0))
    sql, params = cursor.execute.call_args[0]
    assert 'DELETE' in sql
    assert params == (datetime(2025, 8, 15, 10, 0),)