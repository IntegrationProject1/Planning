import os
import json
from datetime import datetime

from event_consumers.queue_consumer import QueueConsumer
from event_consumers.db_consumer import DBClient
from event_consumers.xml_parser import (
    parse_create_event_xml,
    parse_update_event_xml,
    parse_delete_event_xml
)
from event_consumers.calendar_client import CalendarClient, format_rfc3339ms

SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'credentials.json')
IMPERSONATED_USER    = os.getenv('IMPERSONATED_USER')

ROUTING_KEYS = [
    'planning.event.create',
    'planning.event.update',
    'planning.event.delete'
]

def handle_message(routing_key: str, body: bytes):
    rk  = routing_key.replace('_', '.')
    xml = body.decode('utf-8')
    db  = DBClient()

    if not IMPERSONATED_USER:
        raise RuntimeError('IMPERSONATED_USER is niet ingesteld')

    calcli = CalendarClient(SERVICE_ACCOUNT_FILE, IMPERSONATED_USER)

    if rk == 'planning.event.create':
        data = parse_create_event_xml(xml)
        uuid_str = data['uuid']  # GEWIJZIGD: geen format_rfc3339ms

        payload = {
            'uuid':          uuid_str,
            'createdAt':     format_rfc3339ms(datetime.utcnow()),
            'startDateTime': data['start_datetime'].isoformat(),
            'endDateTime':   data['end_datetime'].isoformat(),
            'description':   data['description'],
            'capacity':      data.get('capacity'),
            'organizer':     data.get('organisator'),
            'eventType':     data.get('event_type'),
            'location':      data.get('location')
        }

        new_cal = calcli.create_calendar(
            summary=data['name'],
            description=json.dumps(payload)
        )
        calcli.subscribe_calendar(new_cal['id'])

        now = datetime.utcnow()
        data |= {
            'uuid':         uuid_str,  # zorg dat dit zeker in data zit
            'calendar_id':  new_cal['id'],
            'created_at':   now,
            'last_fetched': now
        }

        db.insert(data)

    elif rk == 'planning.event.update':
        uid, fields = parse_update_event_xml(xml)
        uuid_str = uid  # GEWIJZIGD: geen format_rfc3339ms

        db.update(uuid_str, fields)

        db.cursor.execute(
            "SELECT calendar_id FROM calendars WHERE uuid = %s", (uuid_str,)
        )
        row = db.cursor.fetchone()
        if row and ('start_datetime' in fields or 'end_datetime' in fields):
            cal_id = row['calendar_id']
            items = calcli.service.events().list(calendarId=cal_id).execute().get('items', [])
            if items:
                evt_id = items[0]['id']
                body = {}
                if 'start_datetime' in fields:
                    body.setdefault('start', {})['dateTime'] = fields['start_datetime'].isoformat()
                if 'end_datetime' in fields:
                    body.setdefault('end', {})['dateTime'] = fields['end_datetime'].isoformat()
                calcli.update_event(cal_id, evt_id, body)

        db.update(uuid_str, {'last_fetched': datetime.utcnow()})

    elif rk == 'planning.event.delete':
        uid = parse_delete_event_xml(xml)
        uuid_str = uid  # GEWIJZIGD: geen format_rfc3339ms

        db.cursor.execute(
            "SELECT calendar_id FROM calendars WHERE uuid = %s", (uuid_str,)
        )
        row = db.cursor.fetchone()
        if row:
            calcli.delete_calendar(row['calendar_id'])
        db.delete(uuid_str)

    else:
        print(f"Onbekende routing key: {routing_key}", flush=True)

    db.commit()
    db.close()

def main():
    print("Consumer gestart, wachten op berichten…", flush=True)
    consumer = QueueConsumer(callback=handle_message, routing_keys=ROUTING_KEYS)
    consumer.start_consuming()

if __name__ == '__main__':
    main()
