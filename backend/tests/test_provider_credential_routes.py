from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.credential_schemas import (
    CreateProviderCredentialRequest,
    ProviderSettingsRequest,
    UpdateProviderCredentialRequest,
)
from app.models import Base
from app.routes.settings import (
    activate_credential,
    add_provider_credential,
    delete_credential,
    get_integrations,
    get_provider_credentials,
)
from app.services.settings import get_setting, set_setting


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_credential_request_models_hide_secret_in_repr_and_json() -> None:
    canary = "applykit-secret-canary-schema-1f25"
    requests = [
        ProviderSettingsRequest(model="openai/gpt-5-mini", api_key=canary),
        CreateProviderCredentialRequest(
            label="Personal",
            secret=canary,
            activate=True,
        ),
        UpdateProviderCredentialRequest(secret=canary),
    ]

    for request in requests:
        assert canary not in repr(request)
        assert canary not in request.model_dump_json()


def test_credentials_api_never_returns_raw_secret():
    db = _make_session()
    try:
        created = add_provider_credential(
            "gemini",
            CreateProviderCredentialRequest(
                label="Personal",
                secret="AIza-route-secret",
                activate=True,
            ),
            db,
        ).model_dump()

        assert "secret" not in created
        assert "encrypted_secret" not in created
        assert created["masked_secret"] != "AIza-route-secret"

        listed = get_provider_credentials("gemini", db).model_dump()
        assert listed["credentials"][0]["label"] == "Personal"
        assert "secret" not in listed["credentials"][0]
    finally:
        db.close()


def test_manual_activation_and_deletion_keep_one_active_credential():
    db = _make_session()
    try:
        first = add_provider_credential(
            "openai",
            CreateProviderCredentialRequest(
                label="Personal",
                secret="sk-route-personal",
                activate=True,
            ),
            db,
        )
        second = add_provider_credential(
            "openai",
            CreateProviderCredentialRequest(
                label="Work",
                secret="sk-route-work",
                activate=False,
            ),
            db,
        )

        activated = activate_credential("openai", second.id, db)
        assert activated.is_active is True

        delete_credential("openai", second.id, db)
        remaining = get_provider_credentials("openai", db).credentials
        assert len(remaining) == 1
        assert remaining[0].id == first.id
        assert remaining[0].is_active is True
    finally:
        db.close()


def test_deleting_final_credential_clears_active_model_for_provider():
    db = _make_session()
    try:
        set_setting(db, "llm_provider", "openai/gpt-5-mini")
        credential = add_provider_credential(
            "openai",
            CreateProviderCredentialRequest(
                label="Only key",
                secret="sk-route-only",
                activate=True,
            ),
            db,
        )

        delete_credential("openai", credential.id, db)

        assert get_provider_credentials("openai", db).credentials == []
        assert get_setting(db, "llm_provider") == ""
    finally:
        db.close()


def test_integrations_include_credential_count_and_active_label():
    db = _make_session()
    try:
        add_provider_credential(
            "anthropic",
            CreateProviderCredentialRequest(
                label="Primary",
                secret="sk-ant-primary",
                activate=True,
            ),
            db,
        )
        add_provider_credential(
            "anthropic",
            CreateProviderCredentialRequest(
                label="Backup",
                secret="sk-ant-backup",
                activate=False,
            ),
            db,
        )

        integrations = get_integrations(db).integrations
        anthropic = next(item for item in integrations if item.id == "anthropic")

        assert anthropic.credential_count == 2
        assert anthropic.active_credential_label == "Primary"
        assert anthropic.api_key_configured is True
        assert anthropic.masked_api_key is not None
    finally:
        db.close()
