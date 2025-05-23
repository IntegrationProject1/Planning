import logging
import pika
import os
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    db = DBConsumer()
    cal = CalendarClient()

    def handle_create(ch, method, props, body):
        try:
            data = parse_create_session_xml(body.decode())
            logger.info(f"[CREATE] {data['session_uuid']} — {data['session_name']}")
            db.insert_session(data)
            cal_id = db.get_calendar_id_for_event(data['event_uuid'])
            event_body = {
                'summary':     data['session_name'],
                'description': data.get('session_description'),
                'start':       {'dateTime': data['start_datetime'].isoformat()},
                'end':         {'dateTime': data['end_datetime'].isoformat()},
                'location':    data.get('session_location'),
            }
            created = cal.create_session(cal_id, event_body)
            db.update_google_event_id(data['session_uuid'], created['id'])
            ch.basic_ack(method.delivery_tag)
        except Exception:
            logger.exception("Error in CREATE")
            ch.basic_nack(method.delivery_tag, requeue=False)

    def handle_update(ch, method, props, body):
        try:
            info = parse_update_session_xml(body.decode())
            logger.info(f"[UPDATE] {info['session_uuid']} — changes: {list(info['changes'].keys())}")
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
                if 'session_name' in chg:        body['summary']    = chg['session_name']
                if 'session_description' in chg: body['description']= chg['session_description']
                if 'start_datetime' in chg:      body.setdefault('start',{})['dateTime'] = chg['start_datetime'].isoformat()
                if 'end_datetime' in chg:        body.setdefault('end',{})['dateTime']   = chg['end_datetime'].isoformat()
                if 'session_location' in chg:    body['location']   = chg['session_location']
                if body:
                    cal.update_session(
                        google['calendar_id'], google['google_event_id'], body
                    )
            ch.basic_ack(method.delivery_tag)
        except Exception:
            logger.exception("Error in UPDATE")
            ch.basic_nack(method.delivery_tag, requeue=False)

    def handle_delete(ch, method, props, body):
        try:
            session_uuid = parse_delete_session_xml(body.decode())
            logger.info(f"[DELETE] {session_uuid}")
            google = db.get_google_info_for_session(session_uuid)
            if google and google.get('google_event_id'):
                cal.delete_session(
                    google['calendar_id'], google['google_event_id']
                )
            db.delete_session(session_uuid)
            ch.basic_ack(method.delivery_tag)
        except Exception:
            logger.exception("Error in DELETE")
            ch.basic_nack(method.delivery_tag, requeue=False)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue=QUEUES['create']['queue'], on_message_callback=handle_create
    )
    channel.basic_consume(
        queue=QUEUES['update']['queue'], on_message_callback=handle_update
    )
    channel.basic_consume(
        queue=QUEUES['delete']['queue'], on_message_callback=handle_delete
    )

    logger.info(f"[*] Session consumer started on exchange '{EXCHANGE_NAME}'")
    channel.start_consuming()

if __name__ == '__main__':
    main()
