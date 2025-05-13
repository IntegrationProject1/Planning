import os
import datetime as dt
from dateutil import parser as dateparser
from queue_consumer import QueueConsumer
from xml_parser import (
    parse_create_event_xml,
    parse_update_event_xml,
    parse_delete_event_xml
)
from calendar_client import CalendarClient
from db_consumer import DBClient


def handle_message(routing_key: str, body: bytes):
    xml = body.decode('utf-8')
    # Database configuratie
    db_config = {
        'host': os.environ['MYSQL_HOST'],
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'user': os.environ['MYSQL_USER'],
        'password': os.environ['MYSQL_PASSWORD'],
        'database': os.environ['MYSQL_DATABASE']
    }
    db = DBClient(config=db_config)
    cal = CalendarClient()

    # Afhandelen op basis van routing key
    if routing_key.endswith('.created'):
        data = parse_create_event_xml(xml)
        event_id = cal.create_event(data)
        data['calendar_id'] = event_id
        now = dt.datetime.utcnow()
        data['created_at'] = now
        data['last_fetched'] = now
        db.insert(data)

    elif routing_key.endswith('.updated'):
        uuid, fields = parse_update_event_xml(xml)
        record = db.get_by_uuid(uuid)
        if record:
            # Optioneel datetime-parsing voor legacy velden
            for k, v in fields.items():
                if isinstance(v, str) and 'datetime' in k:
                    fields[k] = dateparser.parse(v)
            cal.update_event(record['calendar_id'], fields)
            # Werk database-record bij
            record.update(fields)
            record['last_fetched'] = dt.datetime.utcnow()
            db.update(record, fields)

    elif routing_key.endswith('.deleted'):
        uuid = parse_delete_event_xml(xml)
        record = db.get_by_uuid(uuid)
        if record:
            cal.delete_event(record['calendar_id'])
            db.delete(uuid)

    db.commit()
    db.close()


if __name__ == '__main__':
    routing_keys = [
        'event.created',
        'event.updated',
        'event.deleted',
    ]
    consumer = QueueConsumer(callback=handle_message, routing_keys=routing_keys)
    consumer.start_polling(interval_seconds=60)
