from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.routes.settings import get_integrations, update_settings
from app.schemas import UpdateSettingsRequest
from app.services.settings import (
    get_provider_api_key,
    set_active_model,
    set_provider_api_key,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_integrations_response_never_exposes_raw_api_key():
    db = _make_session()
    try:
        set_provider_api_key(db, "openai", "sk-secret-value")
        set_active_model(db, "openai/gpt-4o-mini-2024-07-18")

        payload = get_integrations(db).model_dump()
        openai = next(item for item in payload["integrations"] if item["id"] == "openai")

        assert "api_key" not in openai
        assert openai["api_key_configured"] is True
        assert openai["masked_api_key"] != "sk-secret-value"
    finally:
        db.close()


def test_updating_model_without_api_key_preserves_stored_secret():
    db = _make_session()
    try:
        set_provider_api_key(db, "openai", "sk-existing-secret")

        request = UpdateSettingsRequest(
            model="openai/gpt-4.1-mini-2025-04-14",
            api_key=None,
            activate=False,
        )
        update_settings(request, db)

        assert get_provider_api_key(db, "openai") == "sk-existing-secret"
    finally:
        db.close()
