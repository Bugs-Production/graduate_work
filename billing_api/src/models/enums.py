import enum


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class StatusCardsEnum(enum.Enum):
    INIT = "init"
    SUCCESS = "success"
    FAIL = "fail"


class TransactionStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    REFUNDED = "refunded"


class PaymentType(str, enum.Enum):
    STRIPE = "stripe"
    OTHER = "other"
