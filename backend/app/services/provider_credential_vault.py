"""Persistence and lifecycle operations for provider API credentials."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.llm.catalog import CATALOG, provider_from_model
from app.models import AppSetting, ProviderCredential
from app.services.credential_crypto import CredentialCipher, get_credential_cipher

DEFAULT_MAX_PROVIDER_CREDENTIALS = 20


class CredentialVaultError(ValueError):
    """Base error for credential-vault validation failures."""


class CredentialNotFoundError(CredentialVaultError):
    pass


class DuplicateCredentialError(CredentialVaultError):
    pass


class CredentialLimitError(CredentialVaultError):
    pass


def mask_credential(secret: str) -> str:
    if len(secret) <= 8:
        return "•" * len(secret)
    return secret[:4] + "•" * min(len(secret) - 8, 24) + secret[-4:]


def list_provider_credentials(
    db: Session,
    provider_id: str,
) -> list[ProviderCredential]:
    return (
        db.query(ProviderCredential)
        .filter_by(provider_id=provider_id)
        .order_by(
            ProviderCredential.is_active.desc(),
            ProviderCredential.priority.asc(),
            ProviderCredential.id.asc(),
        )
        .all()
    )


def get_provider_credential(
    db: Session,
    provider_id: str,
    credential_id: int,
) -> ProviderCredential | None:
    return (
        db.query(ProviderCredential)
        .filter_by(id=credential_id, provider_id=provider_id)
        .first()
    )


def get_active_provider_credential(
    db: Session,
    provider_id: str,
) -> ProviderCredential | None:
    return (
        db.query(ProviderCredential)
        .filter_by(
            provider_id=provider_id,
            is_active=True,
            is_enabled=True,
        )
        .first()
    )


def decrypt_provider_credential(
    credential: ProviderCredential,
    *,
    cipher: CredentialCipher | None = None,
) -> str:
    return (cipher or get_credential_cipher()).decrypt(credential.encrypted_secret)


def _next_priority(db: Session, provider_id: str) -> int:
    highest = (
        db.query(func.max(ProviderCredential.priority))
        .filter_by(provider_id=provider_id)
        .scalar()
    )
    return int(highest or 0) + 1


def _deactivate_provider_credentials(db: Session, provider_id: str) -> None:
    db.query(ProviderCredential).filter_by(
        provider_id=provider_id,
        is_active=True,
    ).update({"is_active": False}, synchronize_session=False)


def create_provider_credential(
    db: Session,
    *,
    provider_id: str,
    label: str,
    secret: str,
    cipher: CredentialCipher | None = None,
    activate: bool | None = None,
    max_credentials: int = DEFAULT_MAX_PROVIDER_CREDENTIALS,
) -> ProviderCredential:
    provider_id = provider_id.strip()
    label = label.strip()
    secret = secret.strip()
    if not provider_id:
        raise CredentialVaultError("Provider ID is required.")
    if not label:
        raise CredentialVaultError("Credential label is required.")
    if len(label) > 80:
        raise CredentialVaultError("Credential label must be 80 characters or fewer.")
    if not secret:
        raise CredentialVaultError("Credential secret is required.")

    count = db.query(ProviderCredential).filter_by(provider_id=provider_id).count()
    if count >= max_credentials:
        raise CredentialLimitError(
            f"A provider can store at most {max_credentials} credentials."
        )

    selected_cipher = cipher or get_credential_cipher()
    fingerprint = selected_cipher.fingerprint(secret)
    duplicate = (
        db.query(ProviderCredential)
        .filter_by(provider_id=provider_id, fingerprint=fingerprint)
        .first()
    )
    if duplicate:
        raise DuplicateCredentialError(
            "This credential is already stored for the provider."
        )

    should_activate = count == 0 if activate is None else activate
    if should_activate:
        _deactivate_provider_credentials(db, provider_id)

    credential = ProviderCredential(
        provider_id=provider_id,
        label=label,
        encrypted_secret=selected_cipher.encrypt(secret),
        masked_secret=mask_credential(secret),
        fingerprint=fingerprint,
        is_active=should_activate,
        is_enabled=True,
        priority=_next_priority(db, provider_id),
        health_status="unknown",
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def replace_provider_credential_secret(
    db: Session,
    provider_id: str,
    credential_id: int,
    secret: str,
    *,
    cipher: CredentialCipher | None = None,
) -> ProviderCredential:
    credential = get_provider_credential(db, provider_id, credential_id)
    if not credential:
        raise CredentialNotFoundError("Credential was not found.")

    secret = secret.strip()
    if not secret:
        raise CredentialVaultError("Credential secret is required.")
    selected_cipher = cipher or get_credential_cipher()
    fingerprint = selected_cipher.fingerprint(secret)
    duplicate = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.provider_id == provider_id,
            ProviderCredential.fingerprint == fingerprint,
            ProviderCredential.id != credential_id,
        )
        .first()
    )
    if duplicate:
        raise DuplicateCredentialError(
            "This credential is already stored for the provider."
        )

    credential.encrypted_secret = selected_cipher.encrypt(secret)
    credential.masked_secret = mask_credential(secret)
    credential.fingerprint = fingerprint
    credential.health_status = "unknown"
    credential.consecutive_failures = 0
    credential.cooldown_until = None
    credential.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(credential)
    return credential


def rename_provider_credential(
    db: Session,
    provider_id: str,
    credential_id: int,
    label: str,
) -> ProviderCredential:
    credential = get_provider_credential(db, provider_id, credential_id)
    if not credential:
        raise CredentialNotFoundError("Credential was not found.")
    label = label.strip()
    if not label:
        raise CredentialVaultError("Credential label is required.")
    if len(label) > 80:
        raise CredentialVaultError("Credential label must be 80 characters or fewer.")
    credential.label = label
    credential.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(credential)
    return credential


def upsert_active_provider_credential(
    db: Session,
    provider_id: str,
    secret: str,
    *,
    label: str = "Default",
    cipher: CredentialCipher | None = None,
) -> ProviderCredential:
    active = get_active_provider_credential(db, provider_id)
    if active:
        return replace_provider_credential_secret(
            db,
            provider_id,
            active.id,
            secret,
            cipher=cipher,
        )
    return create_provider_credential(
        db,
        provider_id=provider_id,
        label=label,
        secret=secret,
        cipher=cipher,
        activate=True,
    )


def activate_provider_credential(
    db: Session,
    provider_id: str,
    credential_id: int,
) -> ProviderCredential:
    credential = get_provider_credential(db, provider_id, credential_id)
    if not credential or not credential.is_enabled:
        raise CredentialNotFoundError("Credential was not found or is disabled.")

    _deactivate_provider_credentials(db, provider_id)
    credential.is_active = True
    credential.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(credential)
    return credential


def _clear_active_model_for_provider(db: Session, provider_id: str) -> None:
    active_model = db.query(AppSetting).filter_by(key="llm_provider").first()
    if active_model and provider_from_model(active_model.value) == provider_id:
        active_model.value = ""


def delete_provider_credential(
    db: Session,
    provider_id: str,
    credential_id: int,
) -> None:
    credential = get_provider_credential(db, provider_id, credential_id)
    if not credential:
        raise CredentialNotFoundError("Credential was not found.")

    was_active = credential.is_active
    db.delete(credential)
    db.flush()
    if was_active:
        replacement = (
            db.query(ProviderCredential)
            .filter_by(provider_id=provider_id, is_enabled=True)
            .order_by(
                ProviderCredential.priority.asc(),
                ProviderCredential.id.asc(),
            )
            .first()
        )
        if replacement:
            replacement.is_active = True
            replacement.updated_at = datetime.now(UTC)
        else:
            _clear_active_model_for_provider(db, provider_id)
    db.commit()


def clear_provider_credentials(db: Session, provider_id: str) -> None:
    db.query(ProviderCredential).filter_by(provider_id=provider_id).delete(
        synchronize_session=False
    )
    db.commit()


def _get_plain_setting(db: Session, key: str) -> str:
    row = db.query(AppSetting).filter_by(key=key).first()
    return row.value if row else ""


def _clear_plain_setting(db: Session, key: str) -> None:
    row = db.query(AppSetting).filter_by(key=key).first()
    if row:
        row.value = ""


def migrate_legacy_provider_credentials(
    db: Session,
    *,
    cipher: CredentialCipher | None = None,
) -> int:
    """Move old plaintext provider settings into the encrypted vault once."""
    selected_cipher = cipher or get_credential_cipher()
    active_model = _get_plain_setting(db, "llm_provider")
    active_provider = provider_from_model(active_model)
    migrated = 0

    for provider in CATALOG.providers:
        if provider.auth_type.value == "none":
            continue

        provider_key_name = f"api_key_{provider.id}"
        plaintext = _get_plain_setting(db, provider_key_name)
        used_legacy_global = False
        if not plaintext and provider.id == active_provider:
            plaintext = _get_plain_setting(db, "llm_api_key")
            used_legacy_global = bool(plaintext)
        if not plaintext:
            continue

        existing = (
            db.query(ProviderCredential)
            .filter_by(provider_id=provider.id)
            .first()
        )
        if not existing:
            create_provider_credential(
                db,
                provider_id=provider.id,
                label="Default",
                secret=plaintext,
                cipher=selected_cipher,
                activate=True,
            )
            migrated += 1

        _clear_plain_setting(db, provider_key_name)
        if used_legacy_global:
            _clear_plain_setting(db, "llm_api_key")
        db.commit()

    return migrated
