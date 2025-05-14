# File: event_consumers/app.py

import os
import time
from datetime import datetime
from queue_consumer import QueueConsumer
from db_consumer import DBClient
from xml_parser import (
    parse_create_event_xml,
    parse_update_event_xml,
    parse_delete_event_xml
)
from calendar_client import CalendarClient

# Environment-configurable values (hardcoded poll-interval)
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'credentials.json')
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
POLL_INTERVAL = 60  # vaste 60s

# Routing keys
QUEUES = [
    os.getenv('EVENT_CREATED_QUEUE', 'event.created'),
    os.getenv('EVENT_UPDATED_QUEUE', 'event.updated'),
    os.getenv('EVENT_DELETED_QUEUE', 'event.deleted')
]


def handle_message(routing_key: str, body: bytes):
    xml = body.decode('utf-8')
    db = DBClient()
    calcli = CalendarClient(SERVICE_ACCOUNT_FILE)

    if routing_key == QUEUES[0]:  # created
        data = parse_create_event_xml(xml)
        # 1) schrijf in DB (zonder Google-metadata)
        db.insert(data)

        # 2) maak nieuwe Google Calendar aan
        new_cal = calcli.create_calendar(
            summary=data['name'],
            description=data['description']
        )

        # 3) update DB met Google-metadata
        # gebruik 'timeCreated' ipv 'created'
        time_created = new_cal.get('timeCreated')
        if time_created:
            # strip trailing Z en parse
            created_at = datetime.fromisoformat(time_created.rstrip('Z'))
        else:
            created_at = datetime.utcnow()

        db.update(data['uuid'], {
            'calendar_id': new_cal['id'],
            'created_at': created_at,
            'last_fetched': datetime.utcnow()
        })

    elif routing_key == QUEUES[1]:  # updated
        uid, fields = parse_update_event_xml(xml)
        db.update(uid, fields)

        # push update naar Google
        rec = db.cursor.execute(
            "SELECT calendar_id FROM calendars WHERE uuid = %s", (uid,)
        )
        row = db.cursor.fetchone()
        cal_id = row['calendar_id'] if row else None
        if cal_id:
            body = {}
            if 'name' in fields:
                body['summary'] = fields['name']
            if 'description' in fields:
                body['description'] = fields['description']
            if 'start_datetime' in fields:
                body.setdefault('start', {})['dateTime'] = fields['start_datetime'].isoformat(timespec='milliseconds') + 'Z'
            if 'end_datetime' in fields:
                body.setdefault('end', {})['dateTime'] = fields['end_datetime'].isoformat(timespec='milliseconds') + 'Z'
            calcli.update_event(calendar_id=CALENDAR_ID, event_id=cal_id, body=body)

        db.update(uid, {'last_fetched': datetime.utcnow()})

    elif routing_key == QUEUES[2]:  # deleted
        uid = parse_delete_event_xml(xml)
        # delete Google Calendar
        rec = db.cursor.execute(
            "SELECT calendar_id FROM calendars WHERE uuid = %s", (uid,)
        )
        row = db.cursor.fetchone()
        cal_id = row['calendar_id'] if row else None
        if cal_id:
            calcli.delete_calendar(calendar_id=cal_id)
        # delete uit DB
        db.delete(uid)

    else:
        print(f"Onbekende routing_key: {routing_key}", flush=True)

    # commit & close
    db.commit()
    db.close()


def main():
    print("Consumer gestart, verbinden met RabbitMQ...", flush=True)
    consumer = QueueConsumer(
        callback=handle_message,
        routing_keys=QUEUES
    )

    while True:
        print("— Wacht 60s tot volgende poll —", flush=True)
        consumer.poll_once()
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
