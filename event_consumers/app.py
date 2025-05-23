import os
import time
import json
from datetime import datetime

from event_consumers.queue_consumer import QueueConsumer
from event_consumers.db_consumer import DBClient
from event_consumers.xml_parser import (
    parse_create_event_xml,
    parse_update_event_xml,
    parse_delete_event_xml
)
from event_consumers.calendar_client import CalendarClient

# Configuratie via omgevingsvariabelen
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'credentials.json')
IMPERSONATED_USER    = os.getenv('IMPERSONATED_USER')
POLL_INTERVAL        = 60

QUEUES = [
    'planning_event_create',
    'planning_event_update',
    'planning_event_delete'
]

def handle_message(routing_key: str, body: bytes):
    xml = body.decode('utf-8')
    db  = DBClient()

    if not IMPERSONATED_USER:
        raise RuntimeError('IMPERSONATED_USER is niet ingesteld')
    calcli = CalendarClient(SERVICE_ACCOUNT_FILE, IMPERSONATED_USER)

    # CREATE
    if routing_key == QUEUES[0]:
        data = parse_create_event_xml(xml)
        db.insert(data)

        # Bouw payload voor kalender description
        uuid_val = data['uuid']
        uuid_str = uuid_val.isoformat() + 'Z'
        payload = {
            'uuid':          uuid_str,
            'createdAt':     datetime.utcnow().isoformat() + 'Z',
            'startDateTime': data['start_datetime'].isoformat() + 'Z',
            'endDateTime':   data['end_datetime'].isoformat() + 'Z',
            'description':   data['description'],
            'capacity':      data.get('capacity'),
            'organizer':     data.get('organisator') or data.get('organizer'),
            'eventType':     data.get('event_type') or data.get('eventType'),
            'location':      data.get('location')
        }

        # Maak kalender aan
        new_cal = calcli.create_calendar(
            summary=data['name'],
            description=json.dumps(payload)
        )

        calcli.subscribe_calendar(new_cal['id'])

        # Het event (blokje) zelf nooit zichtbaar
        # event_body = {
        #     'summary':     data['name'],
        #     'description': data['description'],
        #     'start':       {'dateTime': data['start_datetime'].isoformat() + 'Z'},
        #     'end':         {'dateTime': data['end_datetime'].isoformat() + 'Z'},
        #     'location':    data.get('location'),
        #     'attendees': [
        #         {'email': u['uuid']} if isinstance(u, dict) else {'email': u}
        #         for u in data.get('registered_users', [])
        #     ]
        # }
        # created_evt = calcli.create_event(new_cal['id'], event_body)

        created_at = datetime.utcnow()
        db.update(data['uuid'], {
            'calendar_id': new_cal['id'],
            'created_at': created_at,
            'last_fetched': datetime.utcnow()
        })

    # UPDATE
    elif routing_key == QUEUES[1]:
        uid, fields = parse_update_event_xml(xml)
        db.update(uid, fields)

        db.cursor.execute(
            "SELECT calendar_id FROM calendars WHERE uuid = %s", (uid,)
        )
        row = db.cursor.fetchone()
        if row:
            cal_id = row['calendar_id']
            events = calcli.service.events().list(calendarId=cal_id).execute()
            items = events.get('items', [])
            if items:
                evt_id = items[0]['id']
                body = {}
                if 'name' in fields:
                    body['summary'] = fields['name']
                if 'description' in fields:
                    body['description'] = fields['description']
                if 'start_datetime' in fields:
                    body.setdefault('start', {})['dateTime'] = (
                        fields['start_datetime'].isoformat() + 'Z'
                    )
                if 'end_datetime' in fields:
                    body.setdefault('end', {})['dateTime'] = (
                        fields['end_datetime'].isoformat() + 'Z'
                    )
                if body:
                    calcli.update_event(cal_id, evt_id, body)

        db.update(uid, {'last_fetched': datetime.utcnow()})

    # DELETE
    elif routing_key == QUEUES[2]:
        uid = parse_delete_event_xml(xml)
        db.cursor.execute(
            "SELECT calendar_id FROM calendars WHERE uuid = %s", (uid,)
        )
        row = db.cursor.fetchone()
        if row:
            calcli.delete_calendar(row['calendar_id'])
        db.delete(uid)

    else:
        print(f"Onbekende routing key: {routing_key}", flush=True)

    db.commit()
    db.close()

def main():
    print("Consumer gestart, verbinden met RabbitMQ...", flush=True)
    consumer = QueueConsumer(
        callback=handle_message,
        routing_keys=QUEUES
    )
    while True:
        consumer.poll_once()
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
