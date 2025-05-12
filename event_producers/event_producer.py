import pika
import os
import json
from datetime import datetime

class QueueClient:
    def __init__(self):
        self.exchange = 'event'
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=os.environ['RABBITMQ_HOST'],
            port=int(os.environ['RABBITMQ_PORT']),
            credentials=pika.PlainCredentials(
                os.environ['RABBITMQ_USER'],
                os.environ['RABBITMQ_PASSWORD']
            )
        ))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=self.exchange, exchange_type='topic', durable=True)

    def send(self, routing_keys, message):
        if isinstance(routing_keys, str):
            routing_keys = [routing_keys]

        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        body = json.dumps(message, default=default_serializer)

        for key in routing_keys:
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=key,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            print(f"Verzonden naar '{key}': {body}", flush=True)

    def close(self):
        self.connection.close()