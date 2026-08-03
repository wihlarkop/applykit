from dataclasses import replace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import AiReadinessTest, AppSetting, Base, ProviderCredential
from app.readiness.ai import (
    ActiveAiConfiguration,
    configuration_fingerprint,
    evaluate_ai_readiness,
    record_active_connection_result,
    resolve_active_ai_configuration,
)
from app.readiness.schemas import AiReadinessStatus, ConnectionFailureCategory


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def config(**overrides) -> ActiveAiConfiguration:
    values = {
        "provider_id": "gemini",
        "model_id": "gemini/gemini-2.5-flash",
        "base_url": None,
        "credential_id": 7,
        "credential_version": 1,
    }
    values.update(overrides)
    return ActiveAiConfiguration(**values)


def add_active_credential(db, provider_id="gemini", credential_id=7, version=1):
    db.add(
        ProviderCredential(
            id=credential_id,
            provider_id=provider_id,
            label="Personal",
            encrypted_secret="ciphertext",
            masked_secret="****1234",
            fingerprint=(provider_id[0] if provider_id else "f") * 64,
            version=version,
            is_active=True,
            is_enabled=True,
            priority=1,
            health_status="healthy",
        )
    )
    db.commit()


def set_active_model(db, model: str):
    db.add(AppSetting(key="llm_provider", value=model))
    db.commit()


def test_same_configuration_has_same_fingerprint() -> None:
    assert configuration_fingerprint(config()) == configuration_fingerprint(config())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider_id", "openai"),
        ("model_id", "gemini/gemini-2.0-flash"),
        ("credential_id", 8),
        ("credential_version", 2),
    ],
)
def test_each_relevant_change_invalidates_fingerprint(field, value) -> None:
    original = config()
    changed = replace(original, **{field: value})
    assert configuration_fingerprint(original) != configuration_fingerprint(changed)



def test_ollama_base_url_change_invalidates_fingerprint() -> None:
    original = config(
        provider_id="ollama",
        model_id="ollama/llama3.2",
        base_url="http://localhost:11434",
        credential_id=None,
        credential_version=None,
    )
    changed = replace(original, base_url="https://ollama.example.com")
    assert configuration_fingerprint(original) != configuration_fingerprint(changed)

def test_ollama_trailing_slash_is_normalized() -> None:
    left = config(
        provider_id="ollama",
        model_id="ollama/llama3.2",
        base_url="https://ollama.example.com/",
        credential_id=None,
        credential_version=None,
    )
    right = replace(left, base_url="https://ollama.example.com")
    assert configuration_fingerprint(left) == configuration_fingerprint(right)


def test_api_key_provider_without_active_credential_is_not_configured() -> None:
    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        assert resolve_active_ai_configuration(db) is None
        assert evaluate_ai_readiness(db).status == AiReadinessStatus.NOT_CONFIGURED
    finally:
        db.close()


def test_ollama_resolves_without_credential() -> None:
    db = make_session()
    try:
        set_active_model(db, "ollama/llama3.2")
        db.add(AppSetting(key="base_url_ollama", value="https://ollama.example.com/"))
        db.commit()

        resolved = resolve_active_ai_configuration(db)
        assert resolved is not None
        assert resolved.base_url == "https://ollama.example.com"
        assert resolved.credential_id is None
        assert resolved.credential_version is None
    finally:
        db.close()


def test_existing_healthy_credential_requires_retest_without_readiness_row() -> None:
    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        add_active_credential(db)

        result = evaluate_ai_readiness(db)
        assert result.status == AiReadinessStatus.RETEST_REQUIRED
        assert result.ready is False
    finally:
        db.close()


def test_successful_matching_row_is_ready() -> None:
    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        add_active_credential(db)
        active = resolve_active_ai_configuration(db)
        assert active is not None
        record_active_connection_result(
            db,
            tested_config=active,
            ok=True,
            public_message="Connection verified.",
        )

        result = evaluate_ai_readiness(db)
        assert result.status == AiReadinessStatus.READY
        assert result.ready is True
    finally:
        db.close()


def test_nonmatching_successful_row_is_configuration_changed() -> None:
    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        add_active_credential(db)
        active = resolve_active_ai_configuration(db)
        assert active is not None
        db.add(
            AiReadinessTest(
                id=1,
                provider_id=active.provider_id,
                model_id="gemini/old-model",
                base_url=None,
                credential_id=active.credential_id,
                credential_version=active.credential_version,
                configuration_fingerprint="x" * 64,
                status="success",
                failure_category=None,
                public_message="Connection verified.",
            )
        )
        db.commit()

        result = evaluate_ai_readiness(db)
        assert result.status == AiReadinessStatus.CONFIGURATION_CHANGED
        assert result.ready is False
    finally:
        db.close()


def test_failed_matching_row_returns_sanitized_category() -> None:
    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        add_active_credential(db)
        active = resolve_active_ai_configuration(db)
        assert active is not None
        record_active_connection_result(
            db,
            tested_config=active,
            ok=False,
            failure_category=ConnectionFailureCategory.AUTHENTICATION_FAILED,
            public_message="Authentication failed. Check the active credential.",
        )

        result = evaluate_ai_readiness(db)
        assert result.status == AiReadinessStatus.AUTHENTICATION_FAILED
        assert result.failure_category == ConnectionFailureCategory.AUTHENTICATION_FAILED
        assert result.message == "Authentication failed. Check the active credential."
    finally:
        db.close()


def test_draft_or_stale_test_does_not_persist() -> None:
    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        add_active_credential(db)
        stale = config(credential_version=9)
        assert record_active_connection_result(
            db,
            tested_config=stale,
            ok=True,
            public_message="Connection verified.",
        ) is None
        assert db.query(AiReadinessTest).count() == 0
    finally:
        db.close()


def test_model_change_invalidates_successful_readiness() -> None:
    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        add_active_credential(db)
        active = resolve_active_ai_configuration(db)
        assert active is not None
        record_active_connection_result(
            db,
            tested_config=active,
            ok=True,
            public_message="Connection verified.",
        )

        db.query(AppSetting).filter_by(key="llm_provider").one().value = (
            "gemini/gemini-2.5-pro"
        )
        db.commit()
        assert evaluate_ai_readiness(db).status == AiReadinessStatus.CONFIGURATION_CHANGED
    finally:
        db.close()


def test_active_credential_change_invalidates_successful_readiness() -> None:
    from app.services.provider_credential_vault import activate_provider_credential

    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        add_active_credential(db, credential_id=7)
        db.add(
            ProviderCredential(
                id=8,
                provider_id="gemini",
                label="Backup",
                encrypted_secret="ciphertext-2",
                masked_secret="****5678",
                fingerprint="b" * 64,
                version=1,
                is_active=False,
                is_enabled=True,
                priority=2,
                health_status="unknown",
            )
        )
        db.commit()
        active = resolve_active_ai_configuration(db)
        assert active is not None
        record_active_connection_result(
            db,
            tested_config=active,
            ok=True,
            public_message="Connection verified.",
        )

        activate_provider_credential(db, "gemini", 8)
        assert evaluate_ai_readiness(db).status == AiReadinessStatus.CONFIGURATION_CHANGED
    finally:
        db.close()


def test_secret_version_change_invalidates_successful_readiness() -> None:
    from cryptography.fernet import Fernet

    from app.services.credential_crypto import CredentialCipher
    from app.services.provider_credential_vault import (
        create_provider_credential,
        replace_provider_credential_secret,
    )

    db = make_session()
    cipher = CredentialCipher(Fernet.generate_key().decode())
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        credential = create_provider_credential(
            db,
            provider_id="gemini",
            label="Primary",
            secret="gemini-original-secret",
            cipher=cipher,
            activate=True,
        )
        active = resolve_active_ai_configuration(db)
        assert active is not None
        record_active_connection_result(
            db,
            tested_config=active,
            ok=True,
            public_message="Connection verified.",
        )

        replace_provider_credential_secret(
            db,
            "gemini",
            credential.id,
            "gemini-replacement-secret",
            cipher=cipher,
        )
        assert evaluate_ai_readiness(db).status == AiReadinessStatus.CONFIGURATION_CHANGED
    finally:
        db.close()


def test_deleting_final_active_credential_becomes_not_configured() -> None:
    from app.services.provider_credential_vault import delete_provider_credential

    db = make_session()
    try:
        set_active_model(db, "gemini/gemini-2.5-flash")
        add_active_credential(db)
        active = resolve_active_ai_configuration(db)
        assert active is not None
        record_active_connection_result(
            db,
            tested_config=active,
            ok=True,
            public_message="Connection verified.",
        )

        delete_provider_credential(db, "gemini", 7)
        assert evaluate_ai_readiness(db).status == AiReadinessStatus.NOT_CONFIGURED
    finally:
        db.close()


def test_ollama_base_url_change_invalidates_successful_readiness() -> None:
    db = make_session()
    try:
        set_active_model(db, "ollama/llama3")
        db.add(AppSetting(key="base_url_ollama", value="http://localhost:11434"))
        db.commit()
        active = resolve_active_ai_configuration(db)
        assert active is not None
        record_active_connection_result(
            db,
            tested_config=active,
            ok=True,
            public_message="Connection verified.",
        )

        db.query(AppSetting).filter_by(key="base_url_ollama").one().value = (
            "https://ollama.example.com"
        )
        db.commit()
        assert evaluate_ai_readiness(db).status == AiReadinessStatus.CONFIGURATION_CHANGED
    finally:
        db.close()
