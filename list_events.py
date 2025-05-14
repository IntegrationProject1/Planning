from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# 1) Maak client
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('calendar', 'v3', credentials=creds)

# 2) Haal alle kalenders op
cals = service.calendarList().list().execute().get('items', [])

# 3) Voor iedere kalender: list events
for cal in cals:
    cid = cal['id']
    summary = cal.get('summary')
    print(f"\n=== Kalender: {summary!r} ({cid}) ===")
    events = service.events().list(
        calendarId=cid,
        timeMin=(datetime.utcnow() - timedelta(days=365)).isoformat()+'Z',
        timeMax=(datetime.utcnow() + timedelta(days=365)).isoformat()+'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])
    if not events:
        print("  (geen events gevonden)")
    for ev in events:
        start = ev['start'].get('dateTime', ev['start'].get('date'))
        print(f" • {start} → {ev['summary']}")
