import asyncio
import json

import litellm
import pytest

from app.exceptions.handlers import generic_exception_handler
from app.exceptions.llm import LLMCallError
from app.exceptions.stream import stream_error_event
from app.routes.settings import test_connection as check_connection
from app.schemas import UpdateSettingsRequest
from app.services import llm as llm_service

_RAW_ERROR = "provider failed api_key=sk-secret-value https://internal.example/debug"


def test_generic_exception_response_does_not_expose_raw_error():
    response = asyncio.run(generic_exception_handler(None, RuntimeError(_RAW_ERROR)))
    payload = json.loads(response.body)

    assert response.status_code == 500
    assert payload == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
        }
    }
    assert "sk-secret-value" not in response.body.decode()
    assert "internal.example" not in response.body.decode()


def test_generic_exception_log_omits_exception_message_and_canary(caplog):
    canary = "applykit-secret-canary-generic-log-b174"
    response = asyncio.run(
        generic_exception_handler(None, RuntimeError(f"provider leaked {canary}"))
    )

    assert response.status_code == 500
    assert canary not in caplog.text
    assert "RuntimeError" in caplog.text


def test_stream_exception_log_omits_exception_message_and_canary(caplog):
    canary = "applykit-secret-canary-stream-log-384c"

    event = stream_error_event(RuntimeError(f"Authorization: Bearer {canary}"))

    assert event.event == "error"
    assert canary not in json.dumps(event.data)
    assert canary not in caplog.text
    assert "RuntimeError" in caplog.text


def test_connection_failure_returns_safe_message(monkeypatch):
    def fail_completion(*args, **kwargs):
        raise RuntimeError(_RAW_ERROR)

    monkeypatch.setattr(litellm, "completion", fail_completion)

    response = check_connection(
        UpdateSettingsRequest(
            model="openai/gpt-4.1-mini",
            api_key="sk-secret-value",
        )
    )

    assert response.ok is False
    assert response.message == (
        "Connection failed. Verify the provider, model, API key, and network settings."
    )
    assert "sk-secret-value" not in response.message


def test_connection_failure_log_omits_provider_exception_message(
    monkeypatch,
    caplog,
):
    canary = "applykit-secret-canary-provider-log-f068"

    def fail_completion(*args, **kwargs):
        raise RuntimeError(f"Authorization: Bearer {canary}")

    monkeypatch.setattr(litellm, "completion", fail_completion)
    response = check_connection(
        UpdateSettingsRequest(
            model="openai/gpt-4.1-mini",
            api_key=canary,
        )
    )

    assert response.ok is False
    assert canary not in response.message
    assert canary not in caplog.text
    assert "RuntimeError" in caplog.text


def test_llm_failure_raises_and_persists_only_safe_message(monkeypatch):
    captured = {}

    def fail_completion(*args, **kwargs):
        raise RuntimeError(_RAW_ERROR)

    def capture_usage(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(llm_service.litellm, "completion", fail_completion)
    monkeypatch.setattr(llm_service, "log_usage_background", capture_usage)

    with pytest.raises(LLMCallError) as exc_info:
        llm_service.call_llm(
            "hello",
            provider="openai/gpt-4.1-mini",
            api_key="sk-secret-value",
            operation="cv_generation",
        )

    assert exc_info.value.message == (
        "The AI provider request failed. Check your settings and try again."
    )
    assert captured["error_message"] == exc_info.value.message
    assert "sk-secret-value" not in captured["error_message"]
