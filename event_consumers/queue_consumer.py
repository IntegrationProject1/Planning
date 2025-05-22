import pika
import os
import time

class QueueConsumer:
    def __init__(self, callback, routing_keys, retries: int = 5, delay: int = 5):
        self.exchange = 'event'
        params = pika.ConnectionParameters(
            host=os.environ['RABBITMQ_HOST'],
            port=int(os.environ['RABBITMQ_PORT']),
            credentials=pika.PlainCredentials(
                os.environ['RABBITMQ_USER'],
                os.environ['RABBITMQ_PASSWORD']
            )
        )
        # Retry-lus voor AMQP-connectie
        for attempt in range(1, retries + 1):
            try:
                self.connection = pika.BlockingConnection(params)
                print(f"Connected to RabbitMQ on attempt {attempt}", flush=True)
                break
            except pika.exceptions.AMQPConnectionError as e:
                print(f"Connection attempt {attempt} failed: {e}. Retrying in {delay}s...", flush=True)
                time.sleep(delay)
        else:
            raise RuntimeError(f"Could not connect to RabbitMQ after {retries} attempts")

        # Kanaal en exchange opzetten
        self.channel = self.connection.channel()
        self.channel.exchange_declare(
            exchange=self.exchange,
            exchange_type='topic',
            durable=True
        )

        # Queues declareren en binden
        self.queue_names = []
        for key in routing_keys:
            queue_name = key
            self.channel.queue_declare(
                queue=queue_name,
                durable=True,
                exclusive=False,
                auto_delete=False
            )
            self.channel.queue_bind(
                exchange=self.exchange,
                queue=queue_name,
                routing_key=key
            )
            self.queue_names.append(queue_name)

        self.callback = callback
        print(f"Listening on queues: {self.queue_names}", flush=True)

    def poll_once(self):
        for queue in self.queue_names:
            method_frame, header_frame, body = self.channel.basic_get(
                queue=queue,
                auto_ack=True
            )
            if method_frame and body:
                routing_key = method_frame.routing_key
                print(f"Polled '{routing_key}' from '{queue}'", flush=True)
                self.callback(routing_key, body)

    def start_polling(self, interval_seconds: int = 60):
        print(f"Starting polling every {interval_seconds} seconds on {self.queue_names}", flush=True)
        try:
            while True:
                self.poll_once()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("Polling stopped by user", flush=True)
            self.connection.close()
