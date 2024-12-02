import json
import logging

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractExchange
from aio_pika.exceptions import AMQPError

logger = logging.getLogger(__name__)


class BaseQueueService:
    """Базовый класс для сервисов, работающих с очередью RabbitMQ."""

    def __init__(self, queue_name: str, exchange: AbstractExchange) -> None:
        self._queue_name = queue_name
        self._exchange = exchange

    async def send_message_to_queue(self, payload: dict) -> bool:
        """Публикует сообщение в очередь RabbitMQ."""
        try:
            message = Message(body=json.dumps(payload).encode(), delivery_mode=DeliveryMode.PERSISTENT)
            await self._exchange.publish(message=message, routing_key=self._queue_name)  # type: ignore[union-attr]
        except (json.JSONDecodeError, TypeError):
            logger.exception(f"Ошибка сериализации данных в JSON при публикации в очередь {self._queue_name}")
            return False
        except AMQPError:
            logger.exception(f"Ошибка RabbitMQ при публикации сообщения в очередь {self._queue_name}")
            return False
        else:
            logger.info(f"Сообщение {payload} успешно опубликовано в очередь {self._queue_name}")
            return True
