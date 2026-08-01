from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.base import AppError, ErrorCode, ErrorBody, ErrorEnvelope
from app.exceptions.infrastructure import InternalApplicationError
from app.exceptions.request import ValidationAppError

logger = logging.getLogger(__name__)

_LEGACY_PUBLIC_MESSAGES = {
    ErrorCode.INTERNAL_SERVER_ERROR: "An unexpected error occurred",
    ErrorCode.LLM_CALL_FAILED: "The AI provider request failed. Check your settings and try again.",
    ErrorCode.PDF_RENDER_FAILED: "Could not generate the PDF. Please try again.",
}


def _response_for(exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_envelope().model_dump(mode="json"),
        headers=exc.headers or None,
    )


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    del request
    return _response_for(exc)


def _legacy_code(value: Any) -> ErrorCode:
    if not isinstance(value, str):
        return ErrorCode.HTTP_ERROR
    try:
        return ErrorCode(value)
    except ValueError:
        return ErrorCode.HTTP_ERROR


def _legacy_message(detail: Any, code: ErrorCode) -> str:
    if code in _LEGACY_PUBLIC_MESSAGES:
        return _LEGACY_PUBLIC_MESSAGES[code]

    candidate: Any = detail
    if isinstance(detail, dict):
        candidate = detail.get("detail", detail.get("message"))
    if isinstance(candidate, str) and candidate.strip():
        return candidate
    return "Request failed."


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    del request
    raw_code = None
    if isinstance(exc.detail, dict):
        raw_code = exc.detail.get("code", exc.detail.get("error_code"))
    code = _legacy_code(raw_code)
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=_legacy_message(exc.detail, code),
            details={},
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump(mode="json"),
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
        "Unhandled exception for %s %s",
        method,
        path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return _response_for(InternalApplicationError())


exception_handlers = {
    AppError: app_exception_handler,
    HTTPException: http_exception_handler,
    RequestValidationError: validation_exception_handler,
    Exception: generic_exception_handler,
}
