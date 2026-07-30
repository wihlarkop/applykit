from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.dependencies import require_llm_config
from app.exceptions.llm import APIKeyNotConfiguredError
from app.models import Base
from app.routes.profile import get_status
from app.routes.settings import update_settings
from app.schemas import UpdateSettingsRequest
from app.services import llm as llm_service
from app.services.settings import (
    get_llm_config,
    get_provider_api_key,
    is_llm_configured,
    provider_requires_api_key,
    set_active_model,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ollama_is_configured_without_an_api_key():
    """Keyless providers are usable without manufacturing a secret."""
    assert provider_requires_api_key("ollama") is False
    assert is_llm_configured("ollama/llama3.2", "") is True
    assert provider_requires_api_key("openai") is True
    assert is_llm_configured("openai/gpt-4.1-mini", "") is False


def test_require_llm_config_accepts_active_ollama_without_secret():
    db = _make_session()
    try:
        set_active_model(db, "ollama/llama3.2")

        assert get_llm_config(db) == ("ollama/llama3.2", "")
        assert require_llm_config(db) == ("ollama/llama3.2", "")
        status = get_status(db)
        assert status.api_key_configured is True
        assert status.provider == "ollama/llama3.2"
    finally:
        db.close()


def test_saving_ollama_does_not_persist_a_placeholder_secret():
    db = _make_session()
    try:
        response = update_settings(
            UpdateSettingsRequest(
                model="ollama/llama3.2",
                api_key=None,
                activate=True,
            ),
            db,
        )

        assert response.api_key_configured is True
        assert get_provider_api_key(db, "ollama") in {None, ""}
    finally:
        db.close()


def test_ollama_call_omits_api_key_argument(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=None,
        )

    monkeypatch.setattr(llm_service.litellm, "completion", fake_completion)

    result = llm_service.call_llm(
        "hello",
        provider="ollama/llama3.2",
        api_key="",
    )

    assert result == "ok"
    assert "api_key" not in captured


def test_secret_provider_still_requires_an_api_key():
    with pytest.raises(APIKeyNotConfiguredError):
        llm_service.call_llm(
            "hello",
            provider="openai/gpt-4.1-mini",
            api_key="",
        )
