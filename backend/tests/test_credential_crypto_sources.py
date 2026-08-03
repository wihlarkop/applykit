from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.config import Settings
from app.services.credential_crypto import (
    CredentialCipher,
    load_external_credential_key,
    load_local_credential_key,
)


def test_environment_key_has_priority_and_is_not_represented_plainly() -> None:
    key = Fernet.generate_key().decode()
    settings = Settings(credential_encryption_key=key)
    assert isinstance(settings.credential_encryption_key, SecretStr)
    assert key not in repr(settings)

    material = load_external_credential_key(settings)
    assert material is not None
    assert material.source == "environment"
    assert CredentialCipher(material.key)


def test_external_key_file_is_read_without_modification(tmp_path: Path) -> None:
    key_path = tmp_path / "credential.key"
    key = Fernet.generate_key()
    key_path.write_bytes(key + b"\n")
    settings = Settings(credential_encryption_key_file=str(key_path))

    material = load_external_credential_key(settings)
    assert material is not None
    assert material.source == "external_file"
    assert material.key == key
    assert key_path.read_bytes() == key + b"\n"


def test_local_key_is_not_created_when_create_is_false(tmp_path: Path) -> None:
    key_path = tmp_path / "credential.key"
    with pytest.raises(FileNotFoundError):
        load_local_credential_key(key_path, create=False)
    assert not key_path.exists()


def test_local_key_creation_uses_restricted_permissions(tmp_path: Path) -> None:
    key_path = tmp_path / "nested" / "credential.key"
    material = load_local_credential_key(key_path, create=True)
    assert material.source == "local_file"
    assert key_path.exists()
    assert key_path.stat().st_mode & 0o777 == 0o600
