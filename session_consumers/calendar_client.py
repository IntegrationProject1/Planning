import os
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class CalendarClient:
    def __init__(self):
        # Path to service account JSON key file
        # Default path to mounted credentials.json, fallback if env var missing
        key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/app/credentials.json')
        # No error if env var missing, we rely on default path
        if not os.path.isfile(key_path):
            raise RuntimeError(f"Service account JSON niet gevonden op {key_path}")

        # User to impersonate (domain-wide delegation)
        subject = os.getenv('IMPERSONATED_USER')
        if not subject:
            raise RuntimeError('IMPERSONATED_USER is niet ingesteld')

        # Load credentials and delegate
        creds = Credentials.from_service_account_file(
            key_path,
            scopes=['https://www.googleapis.com/auth/calendar']
        ).with_subject(subject)

        try:
            self.service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            print(f"Fout bij initialiseren Calendar API: {e}", file=sys.stderr)
            raise

    def create_session(self, calendar_id: str, event_body: dict) -> dict:
        """
        Create a new session event in Google Calendar.
        """
        return self.service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()

    def update_session(self, calendar_id: str, event_id: str, event_body: dict) -> dict:
        """
        Update an existing session event in Google Calendar.
        """
        return self.service.events().patch(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_body
        ).execute()

    def delete_session(self, calendar_id: str, event_id: str) -> None:
        """
        Delete a session event from Google Calendar.
        """
        self.service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
