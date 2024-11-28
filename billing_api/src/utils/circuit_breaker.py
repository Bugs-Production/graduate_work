import enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitBreakerState(str, enum.Enum):
    OPENED = "opened"
    CLOSED = "closed"
    HALF_OPENED = "half_opened"


class CircuitBreaker:
    def __init__(self, error_threshold: int = 5, recovery_timeout: int = 60):  # TODO: сеттингс
        self._errors_count = 0
        self._state = CircuitBreakerState.CLOSED
        self._error_threshold = error_threshold
        self._recovery_timeout = timedelta(seconds=recovery_timeout)
        self._last_opened_time = datetime | None

    def record_failure(self) -> None:
        self._errors_count += 1
        if self._errors_count >= self._error_threshold:
            self._open()

    def record_success(self) -> None:
        self._errors_count = 0
        if self._state == CircuitBreakerState.HALF_OPENED:
            self._close()

    def can_execute(self) -> bool:
        if self._state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPENED]:
            return True
        if self._last_opened_time + self._recovery_timeout <= datetime.now():  # type: ignore[operator]
            self._half_open()
            return True
        return False

    def _open(self):
        self._state = CircuitBreakerState.OPENED
        self._last_opened_time = datetime.now()
        logger.error("CircutBreaker переключен в режим 'ОТКРЫТ'")

    def _half_open(self):
        self._state = CircuitBreakerState.HALF_OPENED
        logger.warning("CircutBreaker переключен в режим 'ПОЛУ-ОТКРЫТ'")

    def _close(self):
        self._state = CircuitBreakerState.CLOSED
        logger.warning("CircutBreaker переключен в режим 'ЗАКРЫТ'")
