import pika
import os

class SessionProducer:
    def __init__(self):
        self.exchange = "session"
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=os.environ["RABBITMQ_HOST"],
            port=int(os.environ["RABBITMQ_PORT"]),
            credentials=pika.PlainCredentials(
                os.environ["RABBITMQ_USER"],
                os.environ["RABBITMQ_PASSWORD"]
            )
        ))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=self.exchange, exchange_type='topic', durable=True)

    def send(self, routing_keys, message):
        if isinstance(routing_keys, str):
            routing_keys = [routing_keys]

        for key in routing_keys:
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=key,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            print(f"\U0001f4e4 Verzonden naar RabbitMQ → '{key}': {message}", flush=True)

    def close(self):
        self.connection.close()