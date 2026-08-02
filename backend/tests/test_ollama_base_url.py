from inspect import signature

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.routes.settings as settings_routes
from app.credential_schemas import ProviderSettingsRequest
from app.exceptions import ValidationAppError
from app.models import Base
from app.routes.settings import (
    disconnect_provider,
    get_integrations,
    test_connection as check_settings_connection,
    update_settings,
)
from app.schemas import TestConnectionResponse as ConnectionTestResponse
from app.services.llm import call_llm, stream_llm
from app.services.settings import get_setting, set_setting


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_disconnect_ollama_clears_model_active_state_and_base_url():
    db = _make_session()
    try:
        set_setting(db, "selected_model_ollama", "ollama/llama3.2")
        set_setting(db, "base_url_ollama", "https://ollama.example.com")
        set_setting(db, "llm_provider", "ollama/llama3.2")

        response = disconnect_provider("ollama", db)
        ollama = next(item for item in response.integrations if item.id == "ollama")

        assert get_setting(db, "selected_model_ollama") in (None, "")
        assert get_setting(db, "base_url_ollama") in (None, "")
        assert get_setting(db, "llm_provider") == ""
        assert ollama.current_model in (None, "")
        assert ollama.is_active is False
    finally:
        db.close()


def test_ollama_integration_exposes_default_base_url():
    db = _make_session()
    try:
        ollama = next(
            item for item in get_integrations(db).integrations if item.id == "ollama"
        )

        assert ollama.base_url == "http://localhost:11434"
    finally:
        db.close()


def test_update_settings_persists_normalized_ollama_base_url():
    db = _make_session()
    try:
        update_settings(
            ProviderSettingsRequest(
                model="ollama/llama3.2",
                api_key=None,
                activate=False,
                base_url="https://ollama.example.com/",
            ),
            db,
        )

        assert get_setting(db, "base_url_ollama") == "https://ollama.example.com"
    finally:
        db.close()


@pytest.mark.parametrize(
    "base_url",
    [
        "ftp://ollama.example.com",
        "http://user:password@ollama.example.com:11434",
        "ollama.example.com:11434",
    ],
)
def test_update_settings_rejects_invalid_ollama_base_url(base_url: str):
    db = _make_session()
    try:
        with pytest.raises(ValidationAppError):
            update_settings(
                ProviderSettingsRequest(
                    model="ollama/llama3.2",
                    api_key=None,
                    activate=False,
                    base_url=base_url,
                ),
                db,
            )
    finally:
        db.close()


def test_connection_passes_draft_ollama_base_url(monkeypatch):
    captured: dict[str, object] = {}

    def fake_test_provider_connection(
        model_id: str,
        api_key: str | None = None,
        **kwargs,
    ) -> ConnectionTestResponse:
        captured["model_id"] = model_id
        captured["api_key"] = api_key
        captured.update(kwargs)
        return ConnectionTestResponse(ok=True, message="Connection successful.")

    monkeypatch.setattr(
        settings_routes,
        "test_provider_connection",
        fake_test_provider_connection,
    )

    result = check_settings_connection(
        ProviderSettingsRequest(
            model="ollama/llama3.2",
            api_key=None,
            activate=False,
            base_url="https://ollama.example.com/",
        )
    )

    assert result.ok is True
    assert captured["api_base"] == "https://ollama.example.com"


def test_llm_request_interfaces_accept_api_base():
    assert "api_base" in signature(call_llm).parameters
    assert "api_base" in signature(stream_llm).parameters
