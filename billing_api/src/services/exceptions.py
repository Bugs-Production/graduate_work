class CardNotFoundException(Exception):
    pass


class UserNotOwnerOfCardException(Exception):
    pass


class ORMBadRequestError(Exception):
    pass


class TransactionNotFoundError(Exception):
    pass
