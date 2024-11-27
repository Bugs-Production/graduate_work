import enum


class BaseEnum(str, enum.Enum):
    @classmethod
    def values(cls):
        return [status.value for status in cls]


class SubscriptionStatus(BaseEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class StatusCardsEnum(BaseEnum):
    INIT = "init"
    SUCCESS = "success"
    FAIL = "fail"


class TransactionStatus(BaseEnum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    REFUNDED = "refunded"


class PaymentType(BaseEnum):
    STRIPE = "stripe"
    OTHER = "other"
