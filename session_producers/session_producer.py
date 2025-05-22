import pika
import os
import time

class SessionProducer:
    def __init__(self):
        self.exchange = "session"
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        """Probeer verbinding te maken met RabbitMQ, met retry-logica."""
        attempt = 0
        while attempt < 3:  # maximaal 3 pogingen
            try:
                print("Probeer verbinding te maken met RabbitMQ...")
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
                print("Verbonden met RabbitMQ.")
                break  # stop met proberen als de verbinding is gelukt
            except pika.exceptions.AMQPConnectionError as e:
                attempt += 1
                print(f"Verbinding mislukt, poging {attempt}/3. Fout: {e}")
                time.sleep(5)  # 5 seconden wachten voor een nieuwe poging

        if attempt == 3:
            raise Exception("Kon geen verbinding maken met RabbitMQ na 3 pogingen.")

    def send(self, routing_keys, message):
        """Verzend berichten naar RabbitMQ met retry-logica."""
        if isinstance(routing_keys, str):
            routing_keys = [routing_keys]

        for key in routing_keys:
            try:
                self.channel.basic_publish(
                    exchange=self.exchange,
                    routing_key=key,
                    body=message,
                    properties=pika.BasicProperties(delivery_mode=2)  # persistent message
                )
                print(f"\U0001f4e4 Verzonden naar RabbitMQ → '{key}': {message}", flush=True)
            except pika.exceptions.StreamLostError as e:
                print(f"StreamLostError opgetreden: {e}")
                print("Probeer opnieuw verbinding te maken en het bericht opnieuw te verzenden.")
                self._connect()  # Verbinding opnieuw proberen
                self.send(key, message)  # Bericht opnieuw verzenden

    def close(self):
        """Sluit de verbinding met RabbitMQ."""
        if self.connection:
            self.connection.close()
            print("RabbitMQ-verbinding gesloten.")
