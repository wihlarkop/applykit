"""Authenticated encryption for provider credentials.

A deployment can supply ``APPLYKIT_CREDENTIAL_ENCRYPTION_KEY``. When it is
absent, ApplyKit creates a persistent Fernet key in a local file so database
backups do not contain the material needed to decrypt provider credentials.
"""

from __future__ import annotations

import hmac
import os
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class CredentialDecryptionError(ValueError):
    """Raised when encrypted credential data cannot be decrypted safely."""


class CredentialCipher:
    """Encrypt, decrypt, and fingerprint provider secrets."""

    def __init__(self, key: str | bytes):
        encoded_key = key.encode() if isinstance(key, str) else key
        try:
            self._fernet = Fernet(encoded_key)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Credential encryption key must be a valid Fernet key."
            ) from exc
        self._fingerprint_key = encoded_key

    def encrypt(self, secret: str) -> str:
        if not secret:
            raise ValueError("Credential secret cannot be empty.")
        return self._fernet.encrypt(secret.encode()).decode()

    def decrypt(self, encrypted_secret: str) -> str:
        try:
            return self._fernet.decrypt(encrypted_secret.encode()).decode()
        except (InvalidToken, UnicodeDecodeError) as exc:
            raise CredentialDecryptionError(
                "Stored credential could not be decrypted. Check the configured "
                "credential encryption key."
            ) from exc

    def fingerprint(self, secret: str) -> str:
        """Return a keyed digest used only for duplicate detection."""
        return hmac.new(
            self._fingerprint_key,
            secret.encode(),
            sha256,
        ).hexdigest()


def _read_key(path: Path) -> bytes:
    key = path.read_bytes().strip()
    if not key:
        raise ValueError(f"Credential key file is empty: {path}")
    return key


def _create_key_file(path: Path) -> bytes:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = Fernet.generate_key()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return _read_key(path)

    with os.fdopen(descriptor, "wb") as handle:
        handle.write(key + b"\n")
    try:
        path.chmod(0o600)
    except OSError:
        # Some filesystems (notably Windows mounts) do not expose POSIX modes.
        pass
    return key


def _load_production_key() -> bytes:
    settings = get_settings()
    if settings.credential_encryption_key:
        return settings.credential_encryption_key.encode()

    key_path = Path(settings.credential_key_file).expanduser()
    if key_path.exists():
        return _read_key(key_path)
    return _create_key_file(key_path)


@lru_cache
def get_credential_cipher() -> CredentialCipher:
    """Return the process-wide credential cipher."""
    return CredentialCipher(_load_production_key())
