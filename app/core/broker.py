from faststream.rabbit import RabbitBroker
from app.core.config import settings, properties

broker = RabbitBroker(properties.RABBITMQ_URL)
