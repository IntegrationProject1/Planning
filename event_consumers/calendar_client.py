import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

class CalendarClient:
    """
    Google Calendar client voor:
     - het aanmaken / updaten / verwijderen van CALENDARS
     - het subscriben (toevoegen) van een kalender in de CalendarList
     - het delen (ACL) van een kalender met een andere user
    """
    def __init__(self, service_account_file: str):
        scopes = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=scopes
        )
        self.service = build('calendar', 'v3', credentials=creds)

    def create_calendar(self, summary: str, description: str) -> dict:
        body = {
            'summary': summary,
            'description': description
        }
        calendar = self.service.calendars().insert(body=body).execute()
        return calendar  # bevat o.a. 'id' en 'created'

    def subscribe_calendar(self, calendar_id: str) -> dict:
        """
        Voeg de kalender toe aan de CalendarList van het service-account.
        Zonder deze stap zie je 'm niet in de UI.
        """
        body = { 'id': calendar_id }
        entry = self.service.calendarList().insert(body=body).execute()
        return entry

    def share_calendar(self, calendar_id: str, user_email: str, role: str = 'writer') -> dict:
        """
        Deel de kalender met een andere gebruiker (bijv. je gmail-account).
        role: 'reader', 'writer' of 'owner'
        """
        body = {
            'role': role,
            'scope': {
                'type': 'user',
                'value': user_email
            }
        }
        rule = self.service.acl().insert(calendarId=calendar_id, body=body).execute()
        return rule

    def create_event(self, calendar_id: str, body: dict) -> dict:
        return self.service.events().insert(calendarId=calendar_id, body=body).execute()

    def update_event(self, calendar_id: str, event_id: str, body: dict) -> dict:
        return self.service.events().patch(calendarId=calendar_id, eventId=event_id, body=body).execute()

    def delete_event(self, calendar_id: str, event_id: str):
        return self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
