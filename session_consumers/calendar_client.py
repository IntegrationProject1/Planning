import os
import sys
import json
from datetime import timezone
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from session_consumers.db_consumer import DBConsumer

def format_rfc3339ms(dt):
    """Zet een datetime om naar RFC3339 met milliseconden en 'Z' suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc) \
             .isoformat(timespec='milliseconds') \
             .replace('+00:00', 'Z')

class CalendarClient:
    def __init__(self):
        key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/app/credentials.json')
        if not os.path.isfile(key_path):
            raise RuntimeError(f"Service account JSON niet gevonden op {key_path}")
        subject = os.getenv('IMPERSONATED_USER')
        if not subject:
            raise RuntimeError('IMPERSONATED_USER is niet ingesteld')

        creds = Credentials.from_service_account_file(
            key_path,
            scopes=['https://www.googleapis.com/auth/calendar']
        ).with_subject(subject)

        try:
            self.service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
        except Exception as e:
            print(f"Fout bij initialiseren Calendar API: {e}", file=sys.stderr)
            raise

    def create_session(self, data: dict) -> dict:
        # Bepaal calendar_id (uit payload of via DB)
        cal_id = data.get('calendar_id')
        if not cal_id:
            db = DBConsumer()
            cal_id = db.get_calendar_id_for_event(data['event_uuid'])
            db.close()

        # Zorg dat alle velden correct in de description komen
        uid = data['session_uuid']
        uuid_str = format_rfc3339ms(uid) if hasattr(uid, 'isoformat') else str(uid)

        payload = {
            'uuid':          uuid_str,
            'guest_speaker': data.get('guest_speaker', []),
            'session_type':  data.get('session_type'),
            'capacity':      data.get('capacity'),
            'description':   data.get('session_description'),
        }

        attendees = [{'email': mail} for mail in data.get('registered_users', [])]

        tz = os.getenv('CALENDAR_TIMEZONE', 'Europe/Brussels')
        event_body = {
            'summary':     data.get('session_name'),
            'description': json.dumps(payload, ensure_ascii=False, indent=2),
            'start': {
                'dateTime': format_rfc3339ms(data['start_datetime']),
                'timeZone': tz
            },
            'end': {
                'dateTime': format_rfc3339ms(data['end_datetime']),
                'timeZone': tz
            },
            'location':    data.get('session_location'),
            'conferenceDataVersion': 0
        }
        if attendees:
            event_body['attendees'] = attendees

        return self.service.events().insert(
            calendarId=cal_id,
            body=event_body,
            conferenceDataVersion=0
        ).execute()

    def update_session(self, data: dict, google_info: dict) -> dict:
        # Zet UUID in payload
        uid = data['session_uuid']
        uuid_str = format_rfc3339ms(uid) if hasattr(uid, 'isoformat') else str(uid)

        payload = {
            'uuid':          uuid_str,
            'guest_speaker': data.get('guest_speaker', []),
            'session_type':  data.get('session_type'),
            'capacity':      data.get('capacity'),
            'description':   data.get('session_description'),
        }
        attendees = [{'email': mail} for mail in data.get('registered_users', [])]

        # Bouw de patch body
        body = {
            'description': json.dumps(payload, ensure_ascii=False, indent=2)
        }
        tz = os.getenv('CALENDAR_TIMEZONE', 'Europe/Brussels')
        if data.get('session_name') is not None:
            body['summary'] = data['session_name']
        if data.get('start_datetime') is not None:
            body.setdefault('start', {})['dateTime'] = format_rfc3339ms(data['start_datetime'])
            body['start']['timeZone'] = tz
        if data.get('end_datetime') is not None:
            body.setdefault('end', {})['dateTime'] = format_rfc3339ms(data['end_datetime'])
            body['end']['timeZone'] = tz
        if data.get('session_location') is not None:
            body['location'] = data['session_location']
        if attendees:
            body['attendees'] = attendees

        return self.service.events().patch(
            calendarId=google_info['google_calendar_id'],
            eventId=google_info['google_event_id'],
            body=body
        ).execute()

    def delete_session(self, calendar_id: str, event_id: str) -> None:
        self.service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
