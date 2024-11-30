import enum

import aio_pika
from aio_pika.abc import AbstractExchange, AbstractRobustConnection

from core.config import settings

connection: AbstractRobustConnection | None = None
exchange: AbstractExchange | None = None


class QueueName(str, enum.Enum):
    AUTH = "auth_events"
    NOTIFICATION = "notification_events"


async def create_rabbitmq_connection(rabbitmq_url: str) -> AbstractRobustConnection:
    return await aio_pika.connect_robust(rabbitmq_url)


async def init_rabbitmq(connection: AbstractRobustConnection) -> AbstractExchange:
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        settings.rabbitmq.exchange_name,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    for queue_name in QueueName:
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(exchange=exchange, routing_key=queue_name)

    return exchange


async def close_rabbitmq_connection(connection: AbstractRobustConnection) -> None:
    await connection.close()


async def get_rabbitmq_exchange() -> AbstractExchange | None:
    return exchange
