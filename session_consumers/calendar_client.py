import os
import sys
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from session_consumers.db_consumer import DBConsumer

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
        # bepaal calendar_id (uit data of via DBConsumer)
        cal_id = data.get('calendar_id')
        if not cal_id:
            db = DBConsumer()
            cal_id = db.get_calendar_id_for_event(data['event_uuid'])
            db.close()

        # zet uuid om naar string
        uid = data['session_uuid']
        uuid_str = uid.isoformat() if hasattr(uid, 'isoformat') else str(uid)

        # bouw JSON-payload: alleen guest speakers
        payload = {
            'uuid':         uuid_str,
            'guestspeaker': data.get('guest_speaker', []),
            'session_type': data.get('session_type'),
            'capacity':     data.get('capacity'),
            'description':  data.get('session_description')
        }

        # alleen geregistreerde gebruikers als attendees
        attendees = [{'email': mail} for mail in data.get('registered_users', [])]

        tz = os.getenv('CALENDAR_TIMEZONE', 'Europe/Brussels')
        event = {
            'summary':     data.get('session_name'),
            'description': json.dumps(payload, indent=2),
            'start':       {'dateTime': data['start_datetime'].isoformat(), 'timeZone': tz},
            'end':         {'dateTime': data['end_datetime'].isoformat(),   'timeZone': tz},
            'location':    data.get('session_location'),
            'conferenceDataVersion': 0
        }
        if attendees:
            event['attendees'] = attendees

        return self.service.events().insert(
            calendarId=cal_id,
            body=event,
            conferenceDataVersion=0
        ).execute()

    def update_session(self, data: dict, google_info: dict) -> dict:
        # vergelijkbaar met create maar patch
        uid = data['session_uuid']
        uuid_str = uid.isoformat() if hasattr(uid, 'isoformat') else str(uid)

        payload = {
            'uuid':         uuid_str,
            'guestspeaker': data.get('guest_speaker', []),
            'session_type': data.get('session_type'),
            'capacity':     data.get('capacity'),
            'description':  data.get('session_description')
        }

        attendees = [{'email': mail} for mail in data.get('registered_users', [])]

        body = {'description': json.dumps(payload, indent=2)}
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
