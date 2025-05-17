import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

class CalendarClient:
    """
    Google Calendar client voor:
     - het aanmaken / updaten / verwijderen van CALENDARS
     - delen van kalenders met andere gebruikers
     - subscriben (toevoegen) van kalenders aan je CalendarList
     - creëren, bijwerken en verwijderen van EVENTS
    """
    def __init__(self, service_account_file: str, subject: str = None):
        scopes = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=scopes
        )
        # subject wordt niet gebruikt (je impliceert geen impersonatie)
        self.service = build('calendar', 'v3', credentials=creds)

    def create_calendar(self, summary: str, description: str) -> dict:
        body = {'summary': summary, 'description': description}
        return self.service.calendars().insert(body=body).execute()

    def share_calendar(self, calendar_id: str, user_email: str, role: str = 'writer') -> dict:
        body = {
            'role': role,
            'scope': {'type': 'user', 'value': user_email}
        }
        return self.service.acl().insert(calendarId=calendar_id, body=body).execute()

    def subscribe_calendar(self, calendar_id: str) -> dict:
        """
        Voegt de gegeven kalender toe aan de CalendarList van de service-account,
        zodat hij in de UI van die account wordt getoond.
        """
        body = {'id': calendar_id}
        return self.service.calendarList().insert(body=body).execute()

    def create_event(self, calendar_id: str, event_body: dict) -> dict:
        return self.service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()

    def update_event(self, calendar_id: str, event_id: str, body: dict) -> dict:
        return self.service.events().patch(
            calendarId=calendar_id,
            eventId=event_id,
            body=body
        ).execute()

    def delete_calendar(self, calendar_id: str):
        return self.service.calendars().delete(
            calendarId=calendar_id
        ).execute()
