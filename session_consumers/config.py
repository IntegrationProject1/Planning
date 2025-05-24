import os

# RabbitMQ-configuratie
RABBIT_HOST    = os.getenv('RABBITMQ_HOST')
RABBIT_PORT    = int(os.getenv('RABBITMQ_PORT', 5672))
RABBIT_USER    = os.getenv('RABBITMQ_USER')
RABBIT_PASS    = os.getenv('RABBITMQ_PASSWORD')
EXCHANGE_NAME  = 'session'
QUEUES = {
    'create': {
        'queue':       'planning_session_create',
        'routing_key': 'planning.session.create',
    },
    'update': {
        'queue':       'planning_session_update',
        'routing_key': 'planning.session.update',
    },
    'delete': {
        'queue':       'planning_session_delete',
        'routing_key': 'planning.session.delete',
    },
}

# MySQL-configuratie
MYSQL_HOST     = os.getenv('MYSQL_HOST')
MYSQL_PORT     = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER     = os.getenv('MYSQL_USER')
MYSQL_PASS     = os.getenv('MYSQL_PASSWORD')
MYSQL_DB       = os.getenv('MYSQL_DATABASE')

# Google-service account
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
IMPERSONATED_USER    = os.getenv('IMPERSONATED_USER')
