"""Failure-safe credential vault initialization and legacy key migration."""

from __future__ import annotations

import hmac
import os
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import ProviderCredential
from app.services.credential_crypto import (
    CredentialCipher,
    CredentialKeyMaterial,
    get_credential_cipher,
    load_external_credential_key,
    load_local_credential_key,
)

SessionFactory = Callable[[], Session]


class CredentialVaultStartupError(RuntimeError):
    """Raised when the credential vault cannot be opened safely."""


def _copy_key_atomically(source: Path, destination: Path) -> None:
    key = source.read_bytes().strip()
    CredentialCipher(key)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(key + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def _credential_count(session_factory: SessionFactory) -> int:
    with session_factory() as db:
        return db.query(ProviderCredential).count()


def _validate_credentials(
    session_factory: SessionFactory,
    cipher: CredentialCipher,
) -> None:
    with session_factory() as db:
        for credential in db.query(ProviderCredential).yield_per(100):
            cipher.decrypt(credential.encrypted_secret)


def _validation_failure() -> CredentialVaultStartupError:
    return CredentialVaultStartupError(
        "Credential vault validation failed.\n"
        "The configured encryption key cannot decrypt existing provider "
        "credentials.\n"
        "Restore the original key or revoke and replace the affected "
        "credentials."
    )


def _select_local_key(
    settings: Settings,
    session_factory: SessionFactory,
) -> tuple[CredentialKeyMaterial, Path | None, bool]:
    active_path = Path(settings.credential_key_file).expanduser()
    legacy_path = (
        Path(settings.credential_legacy_key_file).expanduser()
        if settings.credential_legacy_key_file
        else None
    )
    active_exists = active_path.exists()
    legacy_exists = bool(legacy_path and legacy_path.exists())

    if active_exists and legacy_exists and legacy_path is not None:
        active = load_local_credential_key(active_path, create=False)
        legacy = load_local_credential_key(legacy_path, create=False)
        if not hmac.compare_digest(active.key, legacy.key):
            raise CredentialVaultStartupError(
                "Credential vault migration found different encryption keys in "
                "the active and legacy locations. Restore the correct key and "
                "retry startup."
            )
        return active, legacy_path, False

    if active_exists:
        return load_local_credential_key(active_path, create=False), None, False

    if legacy_exists and legacy_path is not None:
        _copy_key_atomically(legacy_path, active_path)
        get_credential_cipher.cache_clear()
        return load_local_credential_key(active_path, create=False), legacy_path, True

    if _credential_count(session_factory) > 0:
        raise CredentialVaultStartupError(
            "Credential vault key is missing while encrypted provider "
            "credentials already exist. Restore the original key or revoke and "
            "replace the affected credentials."
        )

    material = load_local_credential_key(active_path, create=True)
    get_credential_cipher.cache_clear()
    return material, None, False


def initialize_credential_vault(
    settings: Settings,
    *,
    session_factory: SessionFactory,
) -> None:
    """Select, migrate, and validate the vault key before serving requests."""
    get_credential_cipher.cache_clear()
    external = load_external_credential_key(settings)
    copied_active_path: Path | None = None
    legacy_to_remove: Path | None = None

    if external is not None:
        material = external
    else:
        if settings.deployment_mode == "remote":
            raise CredentialVaultStartupError(
                "Remote mode requires an external credential encryption key."
            )
        material, legacy_to_remove, copied = _select_local_key(
            settings,
            session_factory,
        )
        if copied:
            copied_active_path = Path(settings.credential_key_file).expanduser()

    try:
        _validate_credentials(session_factory, CredentialCipher(material.key))
    except Exception:
        if copied_active_path is not None and copied_active_path.exists():
            copied_active_path.unlink()
            get_credential_cipher.cache_clear()
        raise _validation_failure() from None

    if legacy_to_remove is not None and legacy_to_remove.exists():
        legacy_to_remove.unlink()
        get_credential_cipher.cache_clear()
