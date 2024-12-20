import asyncio
import json
import logging
from abc import ABC, abstractmethod

import httpx
from aio_pika.abc import AbstractIncomingMessage
from aio_pika.exceptions import AMQPError

from core.config import settings
from db import rabbitmq
from utils.circuit_breaker import CircuitBreaker
from workers.exceptions import PermanentWorkerError, TemporaryWorkerError

logger = logging.getLogger(__name__)


class BaseQueueWorker(ABC):
    """Базовый класс для воркеров, обрабатывающих сообщения из очереди и отправляющих запросы
    к внешним сервсиам.
    """

    def __init__(self, queue_name: str):
        self._queue_name = queue_name
        self._circuit_breaker = CircuitBreaker()

    async def process_message(self, message: AbstractIncomingMessage) -> None:
        """Обрабатывает сообщение из очереди."""
        message_info = f"delivery_tag={message.delivery_tag}, timestamp={message.timestamp}"

        if not self._circuit_breaker.can_execute():
            logger.warning(f"Circuit Breaker открыт. Сообщение {message_info} не обработано.")
            return None

        try:
            message_body = json.loads(message.body.decode())
            await self.handle_event(message_body)
            await message.ack()
            self._circuit_breaker.record_success()
        except json.JSONDecodeError as err:
            await message.reject()
            logger.exception(
                f"Невалидный JSON в сообщении {message_info}. Сообщение направлено в DLQ.",
                exc_info=err,
            )
        except PermanentWorkerError as err:
            await message.reject()
            logger.exception(
                f"Неразрешимая ошибка обработки сообщения {message_info}. Сообщение направлено в DLQ.",
                exc_info=err,
            )
        except TemporaryWorkerError as err:
            self._circuit_breaker.record_failure()
            await message.nack(requeue=True)
            logger.exception(
                f"Ошибка обработки сообщения {message_info}. Сообщение возвращено для повторной обработки",
                exc_info=err,
            )

    async def make_post_request(self, url: str, payload: dict) -> None:
        """Делает http-запрос к внешнему сервису."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, json=payload, headers={"X-Service-Secret-Token": settings.secret_token}
                )
                response.raise_for_status()
                self._circuit_breaker.record_success()
                logger.info(f"Запрос к {url} с телом {payload} выполнен успешно.")
            except httpx.HTTPStatusError as err:
                if err.response.is_client_error:
                    raise PermanentWorkerError(
                        f"Ошибка клиента при выполнении запроса к {url} с телом {payload}"
                    ) from err
                self._circuit_breaker.record_failure()
                raise TemporaryWorkerError(f"Ошибка сервера при выполнении запроса к {url} с телом {payload}") from err
            except httpx.RequestError as err:
                self._circuit_breaker.record_failure()
                raise TemporaryWorkerError(
                    f"Ошибка соединения при выполнении запроса к {url} с телом {payload}"
                ) from err

    @abstractmethod
    async def handle_event(self, message_body: dict) -> None:
        raise NotImplementedError


async def run_worker(worker_class: type[BaseQueueWorker], queue_name: str) -> None:
    """Инициализирует и запускает воркер типа worker_class."""
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
        logger.exception(f"Ошибка RabbitMQ. {worker_class.__name__} будет остановлен.")
    except Exception:
        logger.exception(f"Неожиданная ошибка при обработке сообщений воркером {worker_class.__name__}")
    finally:
        await rabbitmq.close_rabbitmq_connection(connection)
