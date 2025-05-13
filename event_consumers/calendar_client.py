import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

class CalendarClient:
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE', 'credentials.json')
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        self.service = build('calendar', 'v3', credentials=credentials)
        self.calendar_id = os.environ['GOOGLE_CALENDAR_ID']
        # Optioneel: maak de tijdzone configureerbaar via env-var
        self.timezone = os.environ.get('GOOGLE_TIMEZONE', 'Europe/Brussels')

    def create_event(self, event_data: dict) -> str:
        event = {
            'summary': event_data['name'],
            'description': event_data['description'],
            'start': {
                'dateTime': event_data['start_datetime'].isoformat(),
                'timeZone': self.timezone
            },
            'end': {
                'dateTime': event_data['end_datetime'].isoformat(),
                'timeZone': self.timezone
            },
            'location': event_data['location'],
        }
        created = self.service.events().insert(
            calendarId=self.calendar_id,
            body=event
        ).execute()
        return created['id']

    def update_event(self, event_id: str, updated_fields: dict) -> dict:
        event = self.service.events().get(
            calendarId=self.calendar_id,
            eventId=event_id
        ).execute()
        # Merge updates, ensuring timeZone is kept
        for key, value in updated_fields.items():
            if key == 'name':
                event['summary'] = value
            elif key == 'description':
                event['description'] = value
            elif key == 'start_datetime':
                event['start'] = {
                    'dateTime': value.isoformat(),
                    'timeZone': self.timezone
                }
            elif key == 'end_datetime':
                event['end'] = {
                    'dateTime': value.isoformat(),
                    'timeZone': self.timezone
                }
            elif key == 'location':
                event['location'] = value
        updated = self.service.events().update(
            calendarId=self.calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        return updated

    def delete_event(self, event_id: str):
        self.service.events().delete(
            calendarId=self.calendar_id,
            eventId=event_id
        ).execute()
