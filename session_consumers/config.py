import os

# RabbitMQ connection parameters
RABBIT_HOST  = os.getenv('RABBITMQ_HOST',  'rabbitmq')
RABBIT_PORT  = int(os.getenv('RABBITMQ_PORT', '5672'))
RABBIT_USER  = os.getenv('RABBITMQ_USER',  'guest')
RABBIT_PASS  = os.getenv('RABBITMQ_PASSWORD', 'guest')

# Topic-exchange voor sessies
EXCHANGE_NAME = 'session'

# Hard-coded queues + routing keys
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
