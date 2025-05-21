import os
import json
import time
from datetime import datetime
from dateutil import parser as dateparser
from googleapiclient.discovery import build
from google.oauth2 import service_account
from event_producers.db_producer import DBClient
from event_producers.event_producer import QueueClient

print("app.py is gestart!", flush=True)

SCOPES = [
    'https://www.googleapis.com/auth/calendar',  # Full access required for domain-wide delegation
]
SERVICE_ACCOUNT_FILE = 'credentials.json'

# Indien vereist, te impersonaten gebruiker via domain-wide delegation
IMPERSONATED_USER = os.getenv('IMPERSONATED_USER')

MYSQL_CONFIG = {
    'host': os.environ['MYSQL_HOST'],
    'user': os.environ['MYSQL_USER'],
    'password': os.environ['MYSQL_PASSWORD'],
    'database': os.environ['MYSQL_DATABASE']
}

def parse_date(date_str):
    if not date_str:
        return None
    try:
        parsed = dateparser.parse(date_str).replace(tzinfo=None)
        print(f"Datum '{date_str}' geparseerd naar: {parsed}", flush=True)
        return parsed
    except Exception as e:
        print(f"Ongeldige datum '{date_str}': {e}", flush=True)
        return None

def get_all_calendars(service):
    print("Ophalen van agenda-lijst...", flush=True)
    result = service.calendarList().list().execute()
    calendars = []

    for cal in result.get('items', []):
        raw_description = cal.get('description', '')
        print(f"Verwerken agenda: {cal.get('summary', '')} (ID: {cal['id']})", flush=True)
        try:
            parsed = json.loads(raw_description)
            print(f"Geldig JSON gevonden: {parsed}", flush=True)
        except Exception as e:
            print(f"Ongeldige JSON in beschrijving voor {cal.get('summary', '')}: {e}", flush=True)
            continue

        if 'uuid' not in parsed:
            print(f"Geen 'uuid' in JSON voor {cal.get('summary', '')}, overslaan...", flush=True)
            continue

        uuid_str = parsed['uuid']
        uuid_dt = parse_date(uuid_str)
        if uuid_dt is None:
            print(f"Ongeldige UUID '{uuid_str}' voor kalender '{cal.get('summary','')}', overslaan...", flush=True)
            continue

        try:
            calendars.append({
                'uuid': uuid_dt,
                'calendar_id': cal['id'],
                'name': cal.get('summary', ''),
                'created_at': parse_date(parsed.get('createdAt')),
                'start_datetime': parse_date(parsed.get('startDateTime')),
                'end_datetime': parse_date(parsed.get('endDateTime')),
                'description': parsed.get('description'),
                'capacity': int(parsed.get('capacity') or 0),
                'organizer': parsed.get('organizer'),
                'event_type': parsed.get('eventType'),
                'location': parsed.get('location'),
                'last_fetched': datetime.utcnow()
            })
            print(f"Agenda toegevoegd aan lijst: {cal.get('summary', '')}", flush=True)
        except Exception as e:
            print(f"Fout bij verwerken kalender '{cal.get('summary', '')}': {e}", flush=True)

    print(f"Totaal {len(calendars)} geldige agenda's gevonden", flush=True)
    return calendars

def detect_changes(old: dict, new: dict) -> dict:
    changed = {}
    fields = ['name', 'start_datetime', 'end_datetime', 'description',
              'capacity', 'organizer', 'event_type', 'location']
    for key in fields:
        old_val = old.get(key)
        new_val = new.get(key)
        old_val_str = old_val.isoformat() if isinstance(old_val, datetime) else str(old_val or '')
        new_val_str = new_val.isoformat() if isinstance(new_val, datetime) else str(new_val or '')
        if old_val_str != new_val_str:
            changed[key] = new_val
            print(f"Wijziging gedetecteerd in veld '{key}': {old_val_str} -> {new_val_str}", flush=True)
    return changed

# --- Main synchronization loop ---
def main():
    print("Laden van Google Calendar credentials...", flush=True)
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    if IMPERSONATED_USER:
        creds = creds.with_subject(IMPERSONATED_USER)
        print(f"Credentials geimpersonateerd naar: {IMPERSONATED_USER}", flush=True)
    print("Credentials succesvol geladen", flush=True)

    print("Bouwen van Google Calendar service...", flush=True)
    service = build('calendar', 'v3', credentials=creds)
    print("Service succesvol gebouwd", flush=True)

    print("Initialiseren van RabbitMQ QueueClient...", flush=True)
    queue = QueueClient()
    print("QueueClient succesvol geïnitialiseerd", flush=True)

    print("Initialiseren van MySQL DBClient...", flush=True)
    db = DBClient(MYSQL_CONFIG, queue)
    print("DBClient succesvol geïnitialiseerd", flush=True)

    calendars = get_all_calendars(service)
    current_uuids = set()
    existing_uuids = db.get_all_uuids()

    for cal in calendars:
        current_uuids.add(cal['uuid'])
        existing = db.get_by_uuid(cal['uuid'])

        if not existing:
            print(f"Nieuwe kalender gedetecteerd: {cal['uuid']}", flush=True)
            cal['uuid'] = cal['uuid'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            db.insert(cal)
        else:
            changes = detect_changes(existing, cal)
            if changes:
                print(f"Updates gedetecteerd voor kalender: {cal['uuid']}", flush=True)
                db.update(cal, changes)

    for uuid in existing_uuids - current_uuids:
        uuid_str = uuid.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"Kalender niet meer aanwezig, verwijderen: {uuid_str}", flush=True)
        db.delete(uuid_str)

    db.commit()
    db.close()
    queue.close()
    print("Sync cyclus voltooid", flush=True)

if __name__ == "__main__":
    print("Event producer gestart!", flush=True)
    while True:
        print(f"\nNieuwe sync gestart om {datetime.utcnow().isoformat()} UTC", flush=True)
        try:
            main()
        except Exception as e:
            print(f"Fout tijdens main(): {e}", flush=True)
        time.sleep(15)
