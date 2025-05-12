import pika
import os
import time
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HeartbeatLogger")

# === RabbitMQ-instellingen ===
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASSWORD")
RABBITMQ_VHOST = "/" 

# === Heartbeat configuratie ===
SERVICE_NAME = "planning_heartbeat"
EXCHANGE_NAME = "heartbeat"
ROUTING_KEY = "controlroom_heartbeat"
HEARTBEAT_INTERVAL = 1  # seconden

# Construeer de XML heartbeat boodschap
def build_heartbeat_xml():
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return f"""
    <Heartbeat>
        <ServiceName>{SERVICE_NAME}</ServiceName>
        <Status>Online</Status>
        <Timestamp>{now_utc}</Timestamp>
        <HeartBeatInterval>{HEARTBEAT_INTERVAL}</HeartBeatInterval>
        <Metadata>
            <Version>1.0</Version>
            <Host>{RABBITMQ_HOST}</Host>
            <Environment>Production</Environment>
        </Metadata>
    </Heartbeat>
    """.strip()

# Maak verbinding met RabbitMQ en geef een kanaal terug
def get_rabbitmq_channel():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )

    for attempt in range(10):
        try:
            logger.info(f"Verbinden met RabbitMQ ({RABBITMQ_HOST}:{RABBITMQ_PORT}, vhost='{RABBITMQ_VHOST}')")
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            return connection, channel
        except Exception as e:
            logger.error(f"Fout bij verbinden (poging {attempt + 1}/10): {e}")
            time.sleep(5)
    raise ConnectionError("Kon geen verbinding maken met RabbitMQ na meerdere pogingen.")

# Verzend de heartbeat naar de opgegeven exchange
def send_heartbeat(channel):
    xml_message = build_heartbeat_xml()
    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=ROUTING_KEY,
        body=xml_message,
        properties=pika.BasicProperties(delivery_mode=2)  # persistent
    )
    logger.info("📡 Heartbeat verzonden")

# Hoofdlus: zend elke seconde een heartbeat
def run_heartbeat():
    try:
        connection, channel = get_rabbitmq_channel()

        # channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="direct", durable=True)

        while True:
            send_heartbeat(channel)
            time.sleep(HEARTBEAT_INTERVAL)
    except KeyboardInterrupt:
        logger.warning("Heartbeat-service handmatig gestopt")
    except Exception as e:
        logger.error(f"Onverwachte fout: {e}")
    finally:
        try:
            connection.close()
            logger.info("Verbinding met RabbitMQ gesloten")
        except:
            pass

if __name__ == "__main__":
    logger.info("Heartbeat-service gestart")
    run_heartbeat()
