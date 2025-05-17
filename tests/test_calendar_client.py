from unittest.mock import MagicMock, patch
from event_consumers.calendar_client import CalendarClient

@patch('event_consumers.calendar_client.service_account.Credentials.from_service_account_file')
@patch('event_consumers.calendar_client.build')
def test_calendar_client_methods(mock_build, mock_creds):
    fake_service = MagicMock()
    fake_service.calendars.return_value.insert.return_value.execute.return_value = {'id': 'cal1'}
    fake_service.acl.return_value.insert.return_value.execute.return_value = {'role': 'writer'}
    fake_service.calendarList.return_value.insert.return_value.execute.return_value = {'id': 'cal1'}
    fake_service.events.return_value.insert.return_value.execute.return_value = {'id': 'evt1'}
    fake_service.events.return_value.patch.return_value.execute.return_value = {'summary': 'updated'}
    fake_service.calendars.return_value.delete.return_value.execute.return_value = None
    mock_build.return_value = fake_service

    # Bypass init
    client = CalendarClient.__new__(CalendarClient)
    client.service = fake_service

    assert client.create_calendar('Sum', 'Desc')['id'] == 'cal1'
    assert client.share_calendar('cal1', 'u@example.com')['role'] == 'writer'
    assert client.subscribe_calendar('cal1')['id'] == 'cal1'
    assert client.create_event('cal1', {'foo': 'bar'})['id'] == 'evt1'
    assert client.update_event('cal1', 'evt1', {'summary': 'X'})['summary'] == 'updated'
    assert client.delete_calendar('cal1') is None