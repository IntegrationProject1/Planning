from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timezone

def format_rfc3339ms(dt):
    """Zet een datetime om naar RFC3339 met ms en 'Z' suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc) \
             .isoformat(timespec='milliseconds') \
             .replace('+00:00', 'Z')

class CalendarClient:
    def __init__(self,
                 service_account_file: str,
                 impersonated_user: str,
                 scopes=None):
        if scopes is None:
            scopes = ['https://www.googleapis.com/auth/calendar']

        self.credentials = (
            service_account.Credentials
            .from_service_account_file(service_account_file, scopes=scopes)
            .with_subject(impersonated_user)
        )
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def create_calendar(self, summary: str, description: str, timezone: str = 'Europe/Brussels') -> dict:
        body = {'summary': summary, 'description': description, 'timeZone': timezone}
        return self.service.calendars().insert(body=body).execute()

    def subscribe_calendar(self, calendar_id: str) -> dict:
        return self.service.calendarList().insert(body={'id': calendar_id}).execute()

    def create_event(self, calendar_id: str, event_body: dict) -> dict:
        uid = event_body.get('id')
        if hasattr(uid, 'isoformat'):
            event_body['id'] = format_rfc3339ms(uid)
        return self.service.events().insert(calendarId=calendar_id, body=event_body).execute()

    def update_event(self, calendar_id: str, event_id: str, event_body: dict) -> dict:
        if hasattr(event_id, 'isoformat'):
            event_id = format_rfc3339ms(event_id)
        return self.service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_body
        ).execute()

    def delete_calendar(self, calendar_id: str):
        return self.service.calendars().delete(calendarId=calendar_id).execute()
