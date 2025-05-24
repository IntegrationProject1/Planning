import pika
import os

rabbitmq_host = os.getenv('RABBITMQ_HOST')
rabbitmq_user = os.getenv('RABBITMQ_USER')
rabbitmq_pass = os.getenv('RABBITMQ_PASS')

credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
parameters = pika.ConnectionParameters(rabbitmq_host, 5672, '/', credentials)
message_event = '<CreateEvent><EventUUID>evt-1</EventUUID><EventName>Test Event</EventName></CreateEvent>'
message_session = '<CreateSession><SessionUUID>sess-1</SessionUUID><SessionName>Test Sessie</SessionName></CreateSession>'
message_update = '<UpdateSession><SessionUUID>sess-1</SessionUUID><SessionName>Updated Sessie</SessionName></UpdateSession>'


def test_event_queue():
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    queues = ['crm.event.create', 'kassa.event.create']
    for q in queues:
        channel.queue_declare(queue=q, durable=True)
        channel.queue_purge(queue=q)
        channel.basic_publish(exchange='', routing_key=q, body=message_event)

    for q in queues:
        method_frame, _, body = channel.basic_get(queue=q)
        assert body.decode() == message_event
        channel.queue_delete(queue=q)
    connection.close()


def test_session_create_queue():
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    queue = 'crm.session.create'
    channel.queue_declare(queue=queue, durable=True)
    channel.queue_purge(queue=queue)
    channel.basic_publish(exchange='', routing_key=queue, body=message_session)
    method_frame, _, body = channel.basic_get(queue=queue)
    assert body.decode() == message_session
    channel.queue_delete(queue=queue)
    connection.close()


def test_session_update_queue():
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    queue = 'crm.session.update'
    channel.queue_declare(queue=queue, durable=True)
    channel.queue_purge(queue=queue)
    channel.basic_publish(exchange='', routing_key=queue, body=message_update)
    method_frame, _, body = channel.basic_get(queue=queue)
    assert body.decode() == message_update
    channel.queue_delete(queue=queue)
    connection.close()