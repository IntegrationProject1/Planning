from google.oauth2 import service_account
from googleapiclient.discovery import build

class CalendarClient:
    def __init__(self,
                 service_account_file: str,
                 impersonated_user: str,
                 scopes=None):
        """
        Wrapper around Google Calendar API with domain-wide delegation.

        :param service_account_file: Path to service account JSON key file
        :param impersonated_user: Email address to impersonate
        :param scopes: List of OAuth scopes
        """
        if scopes is None:
            scopes = ['https://www.googleapis.com/auth/calendar']

        # Load service account credentials and apply impersonation
        self.credentials = (
            service_account.Credentials
            .from_service_account_file(service_account_file, scopes=scopes)
            .with_subject(impersonated_user)
        )

        # Build the Calendar API service
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def create_calendar(self, summary: str, description: str, timezone: str = 'Europe/Brussels') -> dict:
        """
        Create a new calendar.

        :param summary: Calendar name
        :param description: Calendar description
        :param timezone: Timezone for the calendar
        :return: Created calendar resource
        """
        body = {'summary': summary, 'description': description, 'timeZone': timezone}
        return self.service.calendars().insert(body=body).execute()

    def subscribe_calendar(self, calendar_id: str) -> dict:
        """
        Subscribe to an existing calendar so it shows in the calendar list.
        """
        return self.service.calendarList().insert(body={'id': calendar_id}).execute()

    def create_event(self, calendar_id: str, event_body: dict) -> dict:
        """
        Create an event in an existing calendar.
        """
        return self.service.events().insert(calendarId=calendar_id, body=event_body).execute()

    def update_event(self, calendar_id: str, event_id: str, event_body: dict) -> dict:
        """
        Update an existing event.
        """
        return self.service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()

    def delete_calendar(self, calendar_id: str):
        """
        Delete a calendar by ID.
        """
        return self.service.calendars().delete(calendarId=calendar_id).execute()