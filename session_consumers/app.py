import logging
import pika
import json
from session_consumers.config import (
    RABBIT_HOST, RABBIT_PORT, RABBIT_USER, RABBIT_PASS,
    EXCHANGE_NAME, QUEUES
)
from session_consumers.xml_parser import (
    parse_create_session_xml,
    parse_update_session_xml,
    parse_delete_session_xml
)
from session_consumers.db_consumer import DBConsumer
from session_consumers.calendar_client import CalendarClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def handle_create(ch, method, properties, body):
    data = parse_create_session_xml(body)
    db = DBConsumer()

    db.create_session(
        session_uuid        = data['session_uuid'],
        event_uuid          = data['event_uuid'],
        start_datetime      = data['start_datetime'],
        end_datetime        = data['end_datetime'],
        session_name        = data['session_name'],
        session_description = data.get('session_description'),
        session_location    = data.get('session_location'),
        session_type        = data.get('session_type'),
        capacity            = data.get('capacity'),
        guest_speaker       = data.get('guest_speaker', []),
        registered_users    = data.get('registered_users', []),
    )

    calendar_id = db.get_calendar_id_for_event(data['event_uuid'])
    calcli = CalendarClient()

    payload = {
        "uuid":          data['session_uuid'].isoformat() if hasattr(data['session_uuid'], 'isoformat') else data['session_uuid'],
        "guest_speaker": data.get('guest_speaker', []),
        "session_type":  data.get('session_type'),
        "capacity":      data.get('capacity'),
        "description":   data.get('session_description')
    }
    attendees = [{"email": e} for e in data.get('registered_users', [])]

    google_evt = calcli.service.events().insert(
        calendarId=calendar_id,
        body={
            'summary':     data['session_name'],
            'description': json.dumps(payload, ensure_ascii=False, indent=2),
            'start':       {'dateTime': data['start_datetime'].isoformat()},
            'end':         {'dateTime': data['end_datetime'].isoformat()},
            'location':    data.get('session_location'),
            'attendees':   attendees
        }
    ).execute()

    db.save_google_info(
        session_uuid       = data['session_uuid'],
        google_calendar_id = calendar_id,
        google_event_id    = google_evt['id']
    )

    db.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)

def handle_update(ch, method, properties, body):
    info = parse_update_session_xml(body)
    db = DBConsumer()

    db.update_session(
        session_uuid     = info['session_uuid'],
        changes          = info['changes'],
        guest_speaker    = info['changes'].get('guest_speaker'),
        registered_users = info['changes'].get('registered_users'),
    )

    google = db.get_google_info_for_session(info['session_uuid'])
    if google and google.get('google_event_id'):
        body_patch = {}
        chg = info['changes']

        if 'session_name' in chg:
            body_patch['summary'] = chg['session_name']
        if 'start_datetime' in chg:
            body_patch.setdefault('start', {})['dateTime'] = chg['start_datetime'].isoformat()
        if 'end_datetime' in chg:
            body_patch.setdefault('end', {})['dateTime']   = chg['end_datetime'].isoformat()
        if 'session_location' in chg:
            body_patch['location'] = chg['session_location']
        if 'registered_users' in chg:
            body_patch['attendees'] = [{"email": e} for e in chg['registered_users']]

        # opnieuw ophalen volledige payload en gast-lijst verwijderen
        full = db.get_full_session(info['session_uuid'])
        if 'gasten' in full:
            del full['gasten']
        # bouw JSON description zonder gasten
        body_patch['description'] = json.dumps(full, ensure_ascii=False, indent=2)

        calcli = CalendarClient()
        calcli.service.events().patch(
            calendarId=google['google_calendar_id'],
            eventId=google['google_event_id'],
            body=body_patch
        ).execute()

    db.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)

def handle_delete(ch, method, properties, body):
    session_uuid = parse_delete_session_xml(body)
    db = DBConsumer()

    google = db.get_google_info_for_session(session_uuid)
    if google and google.get('google_event_id'):
        calcli = CalendarClient()
        calcli.delete_session(google['google_calendar_id'], google['google_event_id'])

    db.delete_session(session_uuid)
    db.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    params = pika.ConnectionParameters(
        host=RABBIT_HOST, port=RABBIT_PORT, credentials=creds
    )
    conn = pika.BlockingConnection(params)
    channel = conn.channel()

    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)
    for op, cfg in QUEUES.items():
        channel.queue_declare(queue=cfg['queue'], durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=cfg['queue'], routing_key=cfg['routing_key'])

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(QUEUES['create']['queue'], on_message_callback=handle_create, auto_ack=False)
    channel.basic_consume(QUEUES['update']['queue'], on_message_callback=handle_update, auto_ack=False)
    channel.basic_consume(QUEUES['delete']['queue'], on_message_callback=handle_delete, auto_ack=False)

    logger.info("[*] Session consumer gestart met event-driven verwerking via RabbitMQ")
    channel.start_consuming()

if __name__ == '__main__':
    main()
