"""Authenticated encryption for provider credentials.

Managed deployments provide a Fernet key directly or through an externally
mounted file. Local installations use a persistent fallback key file.
"""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings, get_settings
from app.security.secrets import reveal_secret

CredentialKeySource = Literal["environment", "external_file", "local_file"]


@dataclass(frozen=True)
class CredentialKeyMaterial:
    """Loaded Fernet key bytes plus their trusted source."""

    key: bytes
    source: CredentialKeySource


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
    CredentialCipher(key)
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
        handle.flush()
        os.fsync(handle.fileno())
    try:
        path.chmod(0o600)
    except OSError:
        # Some filesystems (notably Windows mounts) do not expose POSIX modes.
        pass
    return key


def load_external_credential_key(
    settings: Settings,
) -> CredentialKeyMaterial | None:
    """Load an explicitly supplied environment or external-file key."""
    direct = reveal_secret(settings.credential_encryption_key).strip()
    if direct:
        key = direct.encode()
        CredentialCipher(key)
        return CredentialKeyMaterial(key=key, source="environment")

    if settings.credential_encryption_key_file:
        path = Path(settings.credential_encryption_key_file).expanduser()
        return CredentialKeyMaterial(key=_read_key(path), source="external_file")

    return None


def load_local_credential_key(
    path: Path,
    *,
    create: bool,
) -> CredentialKeyMaterial:
    """Load or explicitly create the local writable fallback key."""
    expanded = path.expanduser()
    if expanded.exists():
        return CredentialKeyMaterial(key=_read_key(expanded), source="local_file")
    if not create:
        raise FileNotFoundError(expanded)
    return CredentialKeyMaterial(
        key=_create_key_file(expanded),
        source="local_file",
    )


def _load_production_key() -> CredentialKeyMaterial:
    settings = get_settings()
    external = load_external_credential_key(settings)
    if external is not None:
        return external
    if settings.deployment_mode == "remote":
        raise ValueError(
            "Remote mode requires an external credential encryption key."
        )
    return load_local_credential_key(
        Path(settings.credential_key_file),
        create=True,
    )


@lru_cache
def get_credential_cipher() -> CredentialCipher:
    """Return the process-wide credential cipher."""
    return CredentialCipher(_load_production_key().key)
