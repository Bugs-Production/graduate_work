class BaseWorkerError(Exception):
    """Базовый класс для исключений воркеров."""

    pass


class TemporaryWorkerError(BaseWorkerError):
    """Ошибки, связанные с временной недоступностью сервисов.

    При возникновении сообщение нужно вернуть в очередь для повторной обработки.
    """

    pass


class PermanentWorkerError(BaseWorkerError):
    """Ошибки, которые не решатся повторной обработкой.

    При возникновении сообщение нужно отправить в DLQ.
    """

    pass
