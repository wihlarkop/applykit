import ast
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import app.exceptions as exceptions
from app.exceptions import (
    ApplicationNotFoundError,
    FileParseError,
    FileTooLargeError,
    HistoryEntryNotFoundError,
    InvalidRequestError,
    PDFRenderFailedError,
    ProfileNotFoundError,
    ProviderNotFoundError,
    ScrapeFailedError,
    ScrapeValueError,
    UnsupportedFileTypeError,
)
from app.exceptions.handlers import framework_http_exception_handler
from app.exceptions.infrastructure import InternalApplicationError, RateLimitError
from app.exceptions.stream import stream_error_event
from starlette.exceptions import HTTPException as StarletteHTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"


def _request(path: str = "/example", method: str = "GET") -> SimpleNamespace:
    return SimpleNamespace(method=method, url=SimpleNamespace(path=path))


def _payload(response) -> dict:
    return json.loads(response.body)


def test_domain_errors_expose_stable_codes_statuses_and_details():
    cases = [
        (
            ProfileNotFoundError(12),
            404,
            "PROFILE_NOT_FOUND",
            "Profile was not found.",
            {"profile_id": 12},
        ),
        (
            ApplicationNotFoundError(8),
            404,
            "APPLICATION_NOT_FOUND",
            "Application was not found.",
            {"application_id": 8},
        ),
        (
            HistoryEntryNotFoundError("CV entry", 5),
            404,
            "HISTORY_ENTRY_NOT_FOUND",
            "CV entry was not found.",
            {"resource": "CV entry", "entry_id": 5},
        ),
        (
            ProviderNotFoundError("unknown"),
            404,
            "PROVIDER_NOT_FOUND",
            "Provider was not found.",
            {"provider_id": "unknown"},
        ),
        (
            InvalidRequestError("Either url or text must be provided"),
            400,
            "INVALID_REQUEST",
            "Either url or text must be provided",
            {},
        ),
        (
            ScrapeValueError("URL is invalid"),
            422,
            "SCRAPE_VALUE_ERROR",
            "URL is invalid",
            {},
        ),
        (
            ScrapeFailedError(),
            422,
            "SCRAPE_FAILED",
            "Could not extract job posting. Please paste the text manually.",
            {},
        ),
        (
            FileTooLargeError(max_size_mb=5),
            413,
            "FILE_TOO_LARGE",
            "File too large. Maximum size is 5MB.",
            {"max_size_mb": 5},
        ),
        (
            UnsupportedFileTypeError(),
            422,
            "FILE_TYPE_UNSUPPORTED",
            "Unsupported file type. Use PDF, DOCX, or plain text.",
            {},
        ),
        (
            FileParseError(),
            422,
            "FILE_PARSE_FAILED",
            "Could not extract text from file.",
            {},
        ),
        (
            PDFRenderFailedError(),
            502,
            "PDF_RENDER_FAILED",
            "Could not generate the PDF. Please try again.",
            {},
        ),
    ]

    for exc, status, code, message, details in cases:
        assert exc.status_code == status
        assert exc.to_envelope().model_dump(mode="json") == {
            "error": {"code": code, "message": message, "details": details}
        }


def test_framework_http_exception_handler_normalizes_route_not_found():
    response = asyncio.run(
        framework_http_exception_handler(
            _request(path="/missing"),
            StarletteHTTPException(status_code=404, detail="Not Found"),
        )
    )

    assert response.status_code == 404
    assert _payload(response) == {
        "error": {
            "code": "ROUTE_NOT_FOUND",
            "message": "Route was not found.",
            "details": {},
        }
    }


def test_framework_http_exception_handler_sanitizes_server_errors():
    secret = "database password=secret https://internal.example/debug"
    response = asyncio.run(
        framework_http_exception_handler(
            _request(path="/broken"),
            StarletteHTTPException(status_code=503, detail=secret),
        )
    )

    assert response.status_code == 503
    assert _payload(response) == InternalApplicationError().to_envelope().model_dump(
        mode="json"
    )
    assert secret not in response.body.decode()


def test_stream_error_event_uses_native_public_envelope_for_rate_limits():
    event = stream_error_event(RateLimitError(retry_after=3))

    assert event.event == "rate_limit"
    assert event.data == {
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded. Please retry later.",
            "details": {"retry_after": 3},
        }
    }


def test_stream_error_event_sanitizes_unexpected_exceptions():
    secret = "provider api_key=sk-secret https://internal.example"
    event = stream_error_event(RuntimeError(secret))

    assert event.event == "error"
    assert event.data == InternalApplicationError().to_envelope().model_dump(mode="json")
    assert secret not in json.dumps(event.data)


def test_application_code_does_not_use_http_exception():
    candidates = [
        path
        for path in sorted(APP_ROOT.rglob("*.py"))
        if path != APP_ROOT / "exceptions" / "handlers.py"
    ]
    offenders: list[str] = []

    for path in candidates:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in {
                "fastapi",
                "starlette.exceptions",
            }:
                if any(alias.name == "HTTPException" for alias in node.names):
                    offenders.append(f"{path.relative_to(BACKEND_ROOT)}:{node.lineno}")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "HTTPException"
            ):
                offenders.append(f"{path.relative_to(BACKEND_ROOT)}:{node.lineno}")

    assert offenders == []


def test_legacy_exception_compatibility_exports_are_removed():
    legacy_names = {
        "BaseCustomException",
        "ValidationError",
        "InternalServerError",
        "error_response",
        "not_found_404",
    }

    assert {name for name in legacy_names if hasattr(exceptions, name)} == set()
