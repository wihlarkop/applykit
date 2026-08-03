from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.base import AppError, ErrorBody, ErrorCode, ErrorEnvelope
from app.exceptions.infrastructure import InternalApplicationError
from app.exceptions.request import ValidationAppError
from app.security.secrets import safe_exception_type, safe_traceback_locations

logger = logging.getLogger(__name__)


def _response_for(exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_envelope().model_dump(mode="json"),
        headers=exc.headers or None,
    )


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    del request
    return _response_for(exc)


def _framework_error_envelope(exc: StarletteHTTPException) -> ErrorEnvelope:
    if exc.status_code == 404:
        return ErrorEnvelope(
            error=ErrorBody(
                code=ErrorCode.ROUTE_NOT_FOUND,
                message="Route was not found.",
            )
        )
    if exc.status_code == 405:
        return ErrorEnvelope(
            error=ErrorBody(
                code=ErrorCode.METHOD_NOT_ALLOWED,
                message="Method is not allowed for this route.",
            )
        )
    if exc.status_code >= 500:
        return InternalApplicationError().to_envelope()

    message = exc.detail if isinstance(exc.detail, str) and exc.detail.strip() else None
    return ErrorEnvelope(
        error=ErrorBody(
            code=ErrorCode.HTTP_ERROR,
            message=message or "Request failed.",
        )
    )


async def framework_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=exc.status_code,
        content=_framework_error_envelope(exc).model_dump(mode="json"),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "type": str(error.get("type", "validation_error")),
            "location": [str(location) for location in error.get("loc", ())],
            "message": str(error.get("msg", "Invalid input")),
        }
        for error in exc.errors()
    ]
    return await app_exception_handler(
        request,
        ValidationAppError(details={"errors": errors}),
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    method = getattr(request, "method", "UNKNOWN")
    path = getattr(getattr(request, "url", None), "path", "unknown")
    logger.error(
        "Unhandled exception method=%s path=%s error_type=%s locations=%s",
        method,
        path,
        safe_exception_type(exc),
        safe_traceback_locations(exc),
    )
    return _response_for(InternalApplicationError())


exception_handlers = {
    AppError: app_exception_handler,
    StarletteHTTPException: framework_http_exception_handler,
    RequestValidationError: validation_exception_handler,
    Exception: generic_exception_handler,
}
