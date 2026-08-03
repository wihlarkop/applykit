import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import AppSetting, Base, ProviderCredential
from app.services.credential_crypto import CredentialCipher
from app.services.provider_credential_vault import (
    CredentialLimitError,
    DuplicateCredentialError,
    activate_provider_credential,
    create_provider_credential,
    get_active_provider_credential,
    list_provider_credentials,
    migrate_legacy_provider_credentials,
    rename_provider_credential,
    replace_provider_credential_secret,
)
from app.services.settings import get_setting, set_setting


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _cipher() -> CredentialCipher:
    return CredentialCipher(Fernet.generate_key().decode())


def test_provider_credentials_are_encrypted_and_first_key_becomes_active():
    db = _make_session()
    cipher = _cipher()
    try:
        credential = create_provider_credential(
            db,
            provider_id="gemini",
            label="Personal",
            secret="AIza-secret-value",
            cipher=cipher,
        )

        db.refresh(credential)
        assert credential.encrypted_secret != "AIza-secret-value"
        assert "AIza-secret-value" not in credential.encrypted_secret
        assert cipher.decrypt(credential.encrypted_secret) == "AIza-secret-value"
        assert credential.masked_secret.startswith("AIza")
        assert credential.is_active is True
    finally:
        db.close()


def test_multiple_credentials_support_manual_active_selection():
    db = _make_session()
    cipher = _cipher()
    try:
        first = create_provider_credential(
            db,
            provider_id="openai",
            label="Personal",
            secret="sk-personal-secret",
            cipher=cipher,
        )
        second = create_provider_credential(
            db,
            provider_id="openai",
            label="Work",
            secret="sk-work-secret",
            cipher=cipher,
        )

        assert first.is_active is True
        assert second.is_active is False

        activate_provider_credential(db, "openai", second.id)
        active = get_active_provider_credential(db, "openai")

        assert active is not None
        assert active.id == second.id
        assert [item.label for item in list_provider_credentials(db, "openai")] == [
            "Work",
            "Personal",
        ]
    finally:
        db.close()


def test_duplicate_secret_is_rejected_without_storing_a_second_copy():
    db = _make_session()
    cipher = _cipher()
    try:
        create_provider_credential(
            db,
            provider_id="anthropic",
            label="Primary",
            secret="sk-ant-duplicate",
            cipher=cipher,
        )

        try:
            create_provider_credential(
                db,
                provider_id="anthropic",
                label="Duplicate",
                secret="sk-ant-duplicate",
                cipher=cipher,
            )
        except DuplicateCredentialError:
            pass
        else:
            raise AssertionError("duplicate credential should be rejected")

        assert db.query(ProviderCredential).count() == 1
    finally:
        db.close()


def test_credential_limit_is_enforced_per_provider():
    db = _make_session()
    cipher = _cipher()
    try:
        for index in range(2):
            create_provider_credential(
                db,
                provider_id="groq",
                label=f"Key {index + 1}",
                secret=f"gsk-secret-{index}",
                cipher=cipher,
                max_credentials=2,
            )

        try:
            create_provider_credential(
                db,
                provider_id="groq",
                label="Key 3",
                secret="gsk-secret-3",
                cipher=cipher,
                max_credentials=2,
            )
        except CredentialLimitError:
            pass
        else:
            raise AssertionError("credential limit should be enforced")
    finally:
        db.close()


def test_legacy_plaintext_key_migrates_once_and_is_cleared():
    db = _make_session()
    cipher = _cipher()
    try:
        set_setting(db, "api_key_gemini", "AIza-legacy-secret")

        migrated = migrate_legacy_provider_credentials(db, cipher=cipher)
        active = get_active_provider_credential(db, "gemini")

        assert migrated == 1
        assert active is not None
        assert active.label == "Default"
        assert cipher.decrypt(active.encrypted_secret) == "AIza-legacy-secret"
        assert get_setting(db, "api_key_gemini") == ""

        assert migrate_legacy_provider_credentials(db, cipher=cipher) == 0
        assert db.query(ProviderCredential).count() == 1
    finally:
        db.close()


def test_legacy_migration_rolls_back_ciphertext_and_plaintext_together():
    db = _make_session()
    cipher = _cipher()
    plaintext = "applykit-secret-canary-atomic-migration"
    try:
        set_setting(db, "api_key_gemini", plaintext)

        def fail_when_plaintext_is_being_cleared(session) -> None:
            row = session.query(AppSetting).filter_by(key="api_key_gemini").one()
            if row.value == "":
                raise RuntimeError("simulated commit failure")

        event.listen(db, "before_commit", fail_when_plaintext_is_being_cleared)
        with pytest.raises(RuntimeError, match="simulated commit failure"):
            migrate_legacy_provider_credentials(db, cipher=cipher)
        event.remove(db, "before_commit", fail_when_plaintext_is_being_cleared)
        db.rollback()

        assert db.query(ProviderCredential).count() == 0
        assert get_setting(db, "api_key_gemini") == plaintext
    finally:
        db.close()


def test_secret_replacement_increments_version_but_rename_does_not():
    db = _make_session()
    cipher = _cipher()
    try:
        credential = create_provider_credential(
            db,
            provider_id="openai",
            label="Primary",
            secret="sk-original-secret",
            cipher=cipher,
        )
        assert credential.version == 1

        renamed = rename_provider_credential(db, "openai", credential.id, "Renamed")
        assert renamed.version == 1

        replaced = replace_provider_credential_secret(
            db,
            "openai",
            credential.id,
            "sk-replacement-secret",
            cipher=cipher,
        )
        assert replaced.version == 2
    finally:
        db.close()
