from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.routes.settings import (
    test_configured_integration as run_configured_integration_test,
)
from app.services.settings import set_provider_api_key, set_setting


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _successful_completion(**_):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )


def test_configured_integration_uses_saved_model_and_secret(monkeypatch):
    db = _make_session()
    captured = {}

    def completion(**kwargs):
        captured.update(kwargs)
        return _successful_completion()

    monkeypatch.setattr("app.services.provider_connection.litellm.completion", completion)
    try:
        set_setting(db, "selected_model_openai", "openai/gpt-4.1-mini")
        set_provider_api_key(db, "openai", "sk-stored-secret")

        result = run_configured_integration_test("openai", db)

        assert result.ok is True
        assert result.message == "Connection successful."
        assert captured["model"] == "openai/gpt-4.1-mini"
        assert captured["api_key"] == "sk-stored-secret"
    finally:
        db.close()


def test_configured_integration_reports_missing_credential_without_calling_provider(monkeypatch):
    db = _make_session()

    def completion(**_):
        raise AssertionError("provider should not be called")

    monkeypatch.setattr("app.services.provider_connection.litellm.completion", completion)
    try:
        set_setting(db, "selected_model_openai", "openai/gpt-4.1-mini")

        result = run_configured_integration_test("openai", db)

        assert result.ok is False
        assert result.message == "Credential is not configured."
    finally:
        db.close()


def test_configured_integration_uses_catalog_model_when_none_is_saved(monkeypatch):
    db = _make_session()
    captured = {}

    def completion(**kwargs):
        captured.update(kwargs)
        return _successful_completion()

    monkeypatch.setattr("app.services.provider_connection.litellm.completion", completion)
    try:
        set_provider_api_key(db, "gemini", "stored-gemini-key")

        result = run_configured_integration_test("gemini", db)

        assert result.ok is True
        assert captured["model"].startswith("gemini/")
        assert captured["api_key"] == "stored-gemini-key"
    finally:
        db.close()


def test_configured_integration_returns_sanitized_failure(monkeypatch):
    db = _make_session()
    secret = "stored-secret-value"

    def completion(**_):
        raise RuntimeError(f"provider leaked {secret}")

    monkeypatch.setattr("app.services.provider_connection.litellm.completion", completion)
    try:
        set_setting(db, "selected_model_openai", "openai/gpt-4.1-mini")
        set_provider_api_key(db, "openai", secret)

        result = run_configured_integration_test("openai", db)

        assert result.ok is False
        assert result.message == "Provider connection failed."
        assert secret not in result.message
    finally:
        db.close()
