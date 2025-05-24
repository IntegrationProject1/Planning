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
        uuid_str = data['uuid']

        # build the JSON description payload
        payload = {
            'uuid':          uuid_str,
            'createdAt':     format_rfc3339ms(datetime.utcnow()),
            'startDateTime': data['start_datetime'].isoformat() + 'Z',
            'endDateTime':   data['end_datetime'].isoformat() + 'Z',
            'description':   data['description'],
            'capacity':      str(data.get('capacity')),
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
            'calendar_id':  new_cal['id'],
            'created_at':   now,
            'last_fetched': now
        }

        print(f"DEBUG data die wordt opgeslagen: {data}", flush=True)
        db.insert(data)

    elif rk == 'planning.event.update':
        uuid_str, fields = parse_update_event_xml(xml)

        # update our own DB first
        db.update(uuid_str, fields)

        # now pull back the full row
        db.cursor.execute(
            "SELECT uuid, calendar_id, name, created_at, start_datetime, end_datetime, "
            "description, capacity, organizer, event_type, location "
            "FROM calendars WHERE uuid = %s",
            (uuid_str,)
        )
        rec = db.cursor.fetchone()
        if not rec:
            print(f"No DB record for UUID {uuid_str}", flush=True)
            db.commit(); db.close()
            return

        # rebuild the JSON payload
        payload = {
            'uuid':          rec['uuid'],
            'createdAt':     format_rfc3339ms(rec['created_at']),
            'startDateTime': rec['start_datetime'].isoformat() + 'Z',
            'endDateTime':   rec['end_datetime'].isoformat() + 'Z',
            'description':   rec['description'],
            'capacity':      str(rec['capacity']),
            'organizer':     rec['organizer'],
            'eventType':     rec['event_type'],
            'location':      rec['location']
        }
        # update our fetched-timestamp
        payload['lastFetched'] = format_rfc3339ms(datetime.utcnow())

        # push the full JSON back into Calendar.description
        calcli.service.calendars().update(
            calendarId=rec['calendar_id'],
            body={
                'summary':     rec['name'],
                'description': json.dumps(payload),
                'timeZone':    'Europe/Brussels'
            }
        ).execute()

        # finally update last_fetched in our DB
        db.update(uuid_str, {'last_fetched': datetime.utcnow()})

    elif rk == 'planning.event.delete':
        uuid_str = parse_delete_event_xml(xml)

        # pick up calendar_id so we can delete it
        db.cursor.execute("SELECT calendar_id FROM calendars WHERE uuid = %s", (uuid_str,))
        row = db.cursor.fetchone()
        if row and row.get('calendar_id'):
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
