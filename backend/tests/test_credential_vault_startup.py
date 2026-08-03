import sqlite3
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.models import Base
from app.services.credential_crypto import CredentialCipher
from app.services.credential_vault_startup import (
    CredentialVaultStartupError,
    initialize_credential_vault,
)
from app.services.provider_credential_vault import create_provider_credential


def _factory(tmp_path: Path):
    database_path = tmp_path / "applykit.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "deployment_mode": "local",
        "credential_key_file": str(tmp_path / "active" / "credential.key"),
        "credential_legacy_key_file": str(tmp_path / "legacy" / "credential.key"),
    }
    values.update(overrides)
    return Settings(**values)


def _add_credential(factory, key: bytes, secret: str = "stored-secret") -> str:
    cipher = CredentialCipher(key)
    with factory() as db:
        credential = create_provider_credential(
            db,
            provider_id="openai",
            label="Primary",
            secret=secret,
            cipher=cipher,
        )
        return credential.encrypted_secret


def test_fresh_local_install_creates_active_key_only(tmp_path: Path) -> None:
    factory = _factory(tmp_path)
    settings = _settings(tmp_path)

    initialize_credential_vault(settings, session_factory=factory)

    active = Path(settings.credential_key_file)
    legacy = Path(settings.credential_legacy_key_file or "")
    assert active.exists()
    assert active.stat().st_mode & 0o777 == 0o600
    assert not legacy.exists()


def test_existing_encrypted_rows_without_any_key_fail_without_creating_one(
    tmp_path: Path,
) -> None:
    factory = _factory(tmp_path)
    _add_credential(factory, Fernet.generate_key())
    settings = _settings(tmp_path)

    with pytest.raises(CredentialVaultStartupError):
        initialize_credential_vault(settings, session_factory=factory)

    assert not Path(settings.credential_key_file).exists()


def test_legacy_key_moves_atomically_and_credentials_remain_decryptable(
    tmp_path: Path,
) -> None:
    factory = _factory(tmp_path)
    key = Fernet.generate_key()
    ciphertext = _add_credential(factory, key)
    settings = _settings(tmp_path)
    legacy = Path(settings.credential_legacy_key_file or "")
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(key + b"\n")

    initialize_credential_vault(settings, session_factory=factory)

    active = Path(settings.credential_key_file)
    assert active.read_bytes().strip() == key
    assert not legacy.exists()
    assert CredentialCipher(active.read_bytes().strip()).decrypt(ciphertext) == "stored-secret"


def test_stale_temporary_copy_is_cleaned_before_retry(tmp_path: Path) -> None:
    factory = _factory(tmp_path)
    key = Fernet.generate_key()
    _add_credential(factory, key)
    settings = _settings(tmp_path)
    active = Path(settings.credential_key_file)
    legacy = Path(settings.credential_legacy_key_file or "")
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(key + b"\n")
    active.parent.mkdir(parents=True)
    stale = active.with_name(f".{active.name}.tmp")
    stale.write_text("interrupted-copy")

    initialize_credential_vault(settings, session_factory=factory)

    assert active.read_bytes().strip() == key
    assert not stale.exists()
    assert not legacy.exists()


def test_failed_validation_keeps_legacy_and_removes_unverified_copy(
    tmp_path: Path,
) -> None:
    factory = _factory(tmp_path)
    _add_credential(factory, Fernet.generate_key())
    settings = _settings(tmp_path)
    legacy = Path(settings.credential_legacy_key_file or "")
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(Fernet.generate_key() + b"\n")

    with pytest.raises(CredentialVaultStartupError):
        initialize_credential_vault(settings, session_factory=factory)

    assert legacy.exists()
    assert not Path(settings.credential_key_file).exists()


def test_active_and_legacy_same_key_is_idempotent(tmp_path: Path) -> None:
    factory = _factory(tmp_path)
    key = Fernet.generate_key()
    _add_credential(factory, key)
    settings = _settings(tmp_path)
    active = Path(settings.credential_key_file)
    legacy = Path(settings.credential_legacy_key_file or "")
    active.parent.mkdir(parents=True)
    legacy.parent.mkdir(parents=True)
    active.write_bytes(key + b"\n")
    legacy.write_bytes(key + b"\n")

    initialize_credential_vault(settings, session_factory=factory)
    initialize_credential_vault(settings, session_factory=factory)

    assert active.exists()
    assert not legacy.exists()


def test_active_and_legacy_different_keys_fail_closed(tmp_path: Path) -> None:
    factory = _factory(tmp_path)
    settings = _settings(tmp_path)
    active = Path(settings.credential_key_file)
    legacy = Path(settings.credential_legacy_key_file or "")
    active.parent.mkdir(parents=True)
    legacy.parent.mkdir(parents=True)
    active.write_bytes(Fernet.generate_key() + b"\n")
    legacy.write_bytes(Fernet.generate_key() + b"\n")

    with pytest.raises(CredentialVaultStartupError) as exc_info:
        initialize_credential_vault(settings, session_factory=factory)

    assert "different encryption keys" in str(exc_info.value)
    assert active.exists()
    assert legacy.exists()


def test_remote_external_key_must_decrypt_every_credential(tmp_path: Path) -> None:
    factory = _factory(tmp_path)
    correct_key = Fernet.generate_key()
    _add_credential(factory, correct_key)

    valid = _settings(
        tmp_path,
        deployment_mode="remote",
        credential_encryption_key=correct_key.decode(),
    )
    initialize_credential_vault(valid, session_factory=factory)

    invalid = _settings(
        tmp_path,
        deployment_mode="remote",
        credential_encryption_key=Fernet.generate_key().decode(),
    )
    with pytest.raises(CredentialVaultStartupError):
        initialize_credential_vault(invalid, session_factory=factory)


def test_outdated_database_schema_reports_migration_guidance(tmp_path: Path) -> None:
    factory = _factory(tmp_path)
    database_path = tmp_path / "applykit.db"
    with sqlite3.connect(database_path) as db:
        db.execute("ALTER TABLE provider_credential DROP COLUMN version")

    settings = _settings(tmp_path)

    with pytest.raises(CredentialVaultStartupError) as exc_info:
        initialize_credential_vault(settings, session_factory=factory)

    message = str(exc_info.value)
    assert "make migrate" in message
    assert "encryption key cannot decrypt" not in message


def test_startup_error_never_contains_sensitive_values(tmp_path: Path) -> None:
    factory = _factory(tmp_path)
    canary = "applykit-secret-canary-startup-7e4f"
    ciphertext = _add_credential(factory, Fernet.generate_key(), canary)
    settings = _settings(
        tmp_path,
        deployment_mode="remote",
        credential_encryption_key=Fernet.generate_key().decode(),
    )

    with pytest.raises(CredentialVaultStartupError) as exc_info:
        initialize_credential_vault(settings, session_factory=factory)

    message = str(exc_info.value)
    assert canary not in message
    assert ciphertext not in message
