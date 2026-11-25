"""Application errors. Services raise these; `core/handlers.py` turns them into JSON responses."""

from typing import ClassVar


class AppError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "error"
    default_message: ClassVar[str] = "Something went wrong"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)

    @property
    def headers(self) -> dict[str, str] | None:
        return None


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    default_message = "Bad request"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    default_message = "Not authenticated"

    @property
    def headers(self) -> dict[str, str]:
        return {"WWW-Authenticate": "Bearer"}


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    default_message = "You do not have permission to do this"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "Not found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    default_message = "This record conflicts with an existing one"


class UnprocessableError(AppError):
    """A business-rule validation failure tied to one input field (422).

    Rendered in FastAPI's validation format, so the frontend can highlight the field.
    """

    status_code = 422
    code = "validation_error"
    default_message = "Invalid value"

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(message)


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    default_message = "Service temporarily unavailable"
