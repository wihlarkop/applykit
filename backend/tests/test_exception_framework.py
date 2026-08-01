import asyncio
import json
import logging
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.exceptions import AppError, ErrorCode
from app.exceptions.handlers import (
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


class ExampleError(AppError):
    code = ErrorCode.VALIDATION_ERROR
    status_code = 400
    default_message = "Example request failed."


def _request(path: str = "/example", method: str = "GET") -> SimpleNamespace:
    return SimpleNamespace(
        method=method,
        url=SimpleNamespace(path=path),
    )


def _payload(response) -> dict:
    return json.loads(response.body)


def test_app_error_serializes_exact_public_envelope():
    exc = ExampleError(details={"field": "name"})

    assert exc.to_envelope().model_dump(mode="json") == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Example request failed.",
            "details": {"field": "name"},
        }
    }


def test_app_error_cannot_be_instantiated_directly():
    with pytest.raises(TypeError, match="AppError"):
        AppError()


def test_app_error_rejects_invalid_subclass_contract():
    class BrokenError(AppError):
        code = "BROKEN"
        status_code = 400
        default_message = "Broken."

    with pytest.raises(TypeError, match="ErrorCode"):
        BrokenError()


def test_app_error_defensively_copies_details():
    details = {"nested": {"value": 1}}
    exc = ExampleError(details=details)

    details["nested"]["value"] = 2

    assert exc.details == {"nested": {"value": 1}}


def test_app_exception_handler_uses_status_envelope_and_headers():
    exc = ExampleError(
        details={"field": "name"},
        headers={"Retry-After": "5"},
    )

    response = asyncio.run(app_exception_handler(_request(), exc))

    assert response.status_code == 400
    assert response.headers["retry-after"] == "5"
    assert _payload(response) == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Example request failed.",
            "details": {"field": "name"},
        }
    }


def test_http_exception_handler_normalizes_known_legacy_payload():
    exc = HTTPException(
        status_code=400,
        detail={
            "detail": "LLM not configured.",
            "code": "API_KEY_NOT_CONFIGURED",
        },
    )

    response = asyncio.run(http_exception_handler(_request(), exc))

    assert response.status_code == 400
    assert _payload(response) == {
        "error": {
            "code": "API_KEY_NOT_CONFIGURED",
            "message": "LLM not configured.",
            "details": {},
        }
    }


def test_http_exception_handler_uses_safe_code_for_unknown_legacy_code():
    exc = HTTPException(
        status_code=418,
        detail={"detail": "Request rejected.", "code": "RUNTIME_CODE"},
        headers={"X-Reason": "teapot"},
    )

    response = asyncio.run(http_exception_handler(_request(), exc))

    assert response.status_code == 418
    assert response.headers["x-reason"] == "teapot"
    assert _payload(response) == {
        "error": {
            "code": "HTTP_ERROR",
            "message": "Request rejected.",
            "details": {},
        }
    }


def test_http_exception_handler_does_not_reflect_nested_detail_objects():
    secret = "sk-secret-value"
    exc = HTTPException(
        status_code=400,
        detail={"detail": {"api_key": secret}, "code": "UNKNOWN"},
    )

    response = asyncio.run(http_exception_handler(_request(), exc))

    assert _payload(response)["error"]["message"] == "Request failed."
    assert secret not in response.body.decode()


def test_validation_exception_handler_excludes_raw_input():
    secret = "sk-secret-value"
    exc = RequestValidationError(
        [
            {
                "type": "string_type",
                "loc": ("body", "name"),
                "msg": "Input should be a valid string",
                "input": secret,
            }
        ]
    )

    response = asyncio.run(validation_exception_handler(_request(), exc))

    assert response.status_code == 422
    assert _payload(response) == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Validation error.",
            "details": {
                "errors": [
                    {
                        "type": "string_type",
                        "location": ["body", "name"],
                        "message": "Input should be a valid string",
                    }
                ]
            },
        }
    }
    assert secret not in response.body.decode()


def test_generic_exception_handler_sanitizes_response_and_logs_context(caplog):
    secret = "provider failed api_key=sk-secret-value https://internal.example/debug"
    exc = RuntimeError(secret)

    with caplog.at_level(logging.ERROR, logger="app.exceptions.handlers"):
        response = asyncio.run(
            generic_exception_handler(_request(path="/boom", method="POST"), exc)
        )

    assert response.status_code == 500
    assert _payload(response) == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
        }
    }
    assert "sk-secret-value" not in response.body.decode()
    assert "internal.example" not in response.body.decode()
    assert "POST /boom" in caplog.text
