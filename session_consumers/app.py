import logging
import pika
import os
import json
import time
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
        data['session_uuid'],
        data['event_uuid'],
        data['start_datetime'],
        data['end_datetime'],
        data['session_name'],
        data.get('session_description'),
        data.get('session_location'),
        data.get('session_type'),
        data.get('capacity'),
        data.get('guest_speaker', []),
        data.get('registered_users', [])
    )
    # minimale aanpassing: zorg dat calendar_id in data staat
    data['calendar_id'] = db.get_calendar_id_for_event(data['event_uuid'])
    # maak de Calendar-entry
    calcli = CalendarClient()
    google = calcli.create_session(data)
    db.save_google_info(
        data['session_uuid'],
        data['calendar_id'],
        google['id']
    )
    db.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)


def handle_update(ch, method, properties, body):
    info = parse_update_session_xml(body)
    db = DBConsumer()
    db.update_session(
        info['session_uuid'],
        info['changes'],
        guest_speaker=info['changes'].get('guest_speaker'),
        registered_users=info['changes'].get('registered_users')
    )
    google = db.get_google_info_for_session(info['session_uuid'])
    if google and google.get('google_event_id'):
        body = {}
        chg = info['changes']
        if 'session_name' in chg:
            body['summary'] = chg['session_name']
        if 'session_description' in chg:
            body['description'] = chg['session_description']
        if 'start_datetime' in chg:
            body.setdefault('start', {})['dateTime'] = chg['start_datetime'].isoformat()
        if 'end_datetime' in chg:
            body.setdefault('end', {})['dateTime'] = chg['end_datetime'].isoformat()
        if 'session_location' in chg:
            body['location'] = chg['session_location']
        calcli = CalendarClient()
        calcli.service.events().patch(
            calendarId=google['google_calendar_id'],
            eventId=google['google_event_id'],
            body=body
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
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        credentials=credentials,
    )
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)
    for op, cfg in QUEUES.items():
        channel.queue_declare(queue=cfg['queue'], durable=True)
        channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=cfg['queue'],
            routing_key=cfg['routing_key']
        )

    channel.basic_qos(prefetch_count=1)

    logger.info(f"[*] Session consumer gestart (1 pull per 60s)")
    POLL_INTERVAL = 60
    while True:
        for op, handler in [
            ('create', handle_create),
            ('update', handle_update),
            ('delete', handle_delete),
        ]:
            method, props, body = channel.basic_get(
                queue=QUEUES[op]['queue'],
                auto_ack=False
            )
            if method:
                handler(channel, method, props, body)
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
