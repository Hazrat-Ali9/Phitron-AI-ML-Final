"""Global exception handlers: every error leaves the API as JSON, never as a traceback."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError, UnprocessableError

logger = logging.getLogger(__name__)


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    if isinstance(exc, UnprocessableError):
        detail: object = [{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}]
    else:
        detail = exc.message
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail, "code": exc.code},
        headers=exc.headers,
    )


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Keep FastAPI's list format ({loc, msg, type}); the frontend maps `loc` to form fields.
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(exc.errors()), "code": "validation_error"},
    )


async def integrity_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Safety net: services check duplicates first and raise ConflictError with a clear message.
    logger.warning("IntegrityError reached the global handler: %s", getattr(exc, "orig", exc))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "This record conflicts with an existing one", "code": "conflict"},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "code": "internal_error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
