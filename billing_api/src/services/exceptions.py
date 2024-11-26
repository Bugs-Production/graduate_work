from http import HTTPStatus

from fastapi.exceptions import HTTPException


class CardNotFoundException(Exception):
    pass


class UserNotOwnerOfCardException(Exception):
    pass


class ORMBadRequestError(Exception):
    pass


class TransactionNotFoundError(Exception):
    pass


class ObjectNotFoundError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=detail)


class ObjectAlreadyExistsError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=detail)
