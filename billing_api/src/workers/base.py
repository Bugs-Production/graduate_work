import asyncio
import json
import logging
from abc import ABC, abstractmethod

from aio_pika.abc import AbstractIncomingMessage
from aio_pika.exceptions import AMQPError

from core.config import settings
from db import rabbitmq
from utils.circuit_breaker import CircuitBreaker
from workers.exceptions import PermanentWorkerError, TemporaryWorkerError

logger = logging.getLogger(__name__)


class BaseQueueWorker(ABC):
    def __init__(self, queue_name: str):
        self._queue_name = queue_name
        self._circuit_breaker = CircuitBreaker()

    async def process_message(self, message: AbstractIncomingMessage) -> None:
        if not self._circuit_breaker.can_execute():
            logger.warning("Circuit Breaker открыт. Обработка сообщений остановлена")
            return None

        try:
            message_body = json.loads(message.body.decode())
            await self.handle_event(message_body)
            await message.ack()
            self._circuit_breaker.record_success()
        except json.JSONDecodeError as err:
            await message.reject()
            logger.exception(
                f"Невалидный JSON в сообщении {message.message_id}. Сообщение направлено в DLQ.",
                exc_info=err,
            )
        except PermanentWorkerError as err:
            await message.reject()
            logger.exception(
                f"Неразрешимая ошибка обработки сообщения {message.message_id}. Сообщение направлено в DLQ.",
                exc_info=err,
            )
        except TemporaryWorkerError as err:
            self._circuit_breaker.record_failure()
            await message.nack(requeue=True)
            logger.exception(
                f"Ошибка обработки сообщения {message.message_id}. Сообщение возвращено для повторной обработки",
                exc_info=err,
            )

    @abstractmethod
    async def handle_event(self, message_body: dict) -> None:
        raise NotImplementedError


async def run_worker(worker_class: type[BaseQueueWorker], queue_name: str) -> None:
    worker = worker_class(queue_name)

    connection = await rabbitmq.create_rabbitmq_connection(settings.rabbitmq.url)
    await rabbitmq.init_rabbitmq(connection)
    channel = await connection.channel()
    queue = await channel.get_queue(queue_name)

    logger.info(f"Запущен воркер {worker_class.__name__}")

    try:
        await queue.consume(worker.process_message)
        await asyncio.Future()
    except AMQPError:
        logger.exception("Ошибка RabbitMQ. AuthWorker будет остановлен.")
    except Exception:
        logger.exception("Неожиданная ошибка при обработке сообщений воркером AuthWorker")
    finally:
        await rabbitmq.close_rabbitmq_connection(connection)
