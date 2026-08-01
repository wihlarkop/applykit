"""Credential strategy selection and bounded provider-key rotation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TypeVar

from sqlalchemy.orm import Session

from app.models import ProviderCredential, ProviderCredentialPolicy
from app.services.credential_crypto import CredentialCipher, get_credential_cipher
from app.services.provider_credential_vault import decrypt_provider_credential

ResultT = TypeVar("ResultT")
MAX_ROTATION_ATTEMPTS = 5
DEFAULT_TEMPORARY_COOLDOWN_SECONDS = 30
DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 60


class CredentialStrategy(StrEnum):
    MANUAL = "manual"
    FAILOVER = "failover"
    ROUND_ROBIN = "round_robin"


class CredentialFailureKind(StrEnum):
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TEMPORARY = "temporary"
    NON_RETRYABLE = "non_retryable"


class CredentialAttemptError(Exception):
    """Internal typed failure used by the rotation executor."""

    def __init__(
        self,
        kind: CredentialFailureKind,
        *,
        retry_after: float | None = None,
        original: Exception | None = None,
    ) -> None:
        self.kind = kind
        self.retry_after = retry_after
        self.original = original
        super().__init__(kind.value)


class NoEligibleCredentialError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _db_datetime(value: datetime) -> datetime:
    """SQLite persists UTC timestamps without timezone metadata."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def get_credential_policy(
    db: Session,
    provider_id: str,
) -> ProviderCredentialPolicy:
    policy = db.query(ProviderCredentialPolicy).filter_by(provider_id=provider_id).first()
    if policy:
        return policy

    policy = ProviderCredentialPolicy(
        provider_id=provider_id,
        strategy=CredentialStrategy.MANUAL.value,
        max_attempts=2,
        round_robin_cursor=0,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_credential_policy(
    db: Session,
    provider_id: str,
    *,
    strategy: CredentialStrategy | str,
    max_attempts: int,
) -> ProviderCredentialPolicy:
    try:
        normalized_strategy = CredentialStrategy(strategy)
    except ValueError as exc:
        raise ValueError("Unsupported credential strategy.") from exc
    if not 1 <= max_attempts <= MAX_ROTATION_ATTEMPTS:
        raise ValueError(
            f"Maximum attempts must be between 1 and {MAX_ROTATION_ATTEMPTS}."
        )

    policy = get_credential_policy(db, provider_id)
    policy.strategy = normalized_strategy.value
    policy.max_attempts = max_attempts
    if normalized_strategy is not CredentialStrategy.ROUND_ROBIN:
        policy.round_robin_cursor = 0
    policy.updated_at = _db_datetime(_utc_now())
    db.commit()
    db.refresh(policy)
    return policy


def _is_eligible(credential: ProviderCredential, now: datetime) -> bool:
    if not credential.is_enabled:
        return False
    if credential.cooldown_until is None:
        return True
    cooldown = credential.cooldown_until
    comparable_now = _db_datetime(now)
    if cooldown.tzinfo is not None:
        cooldown = _db_datetime(cooldown)
    return cooldown <= comparable_now


def _eligible_credentials(
    db: Session,
    provider_id: str,
    now: datetime,
) -> list[ProviderCredential]:
    credentials = (
        db.query(ProviderCredential)
        .filter_by(provider_id=provider_id)
        .order_by(
            ProviderCredential.priority.asc(),
            ProviderCredential.id.asc(),
        )
        .all()
    )
    return [credential for credential in credentials if _is_eligible(credential, now)]


def _ordered_candidates(
    credentials: list[ProviderCredential],
    policy: ProviderCredentialPolicy,
) -> list[ProviderCredential]:
    strategy = CredentialStrategy(policy.strategy)
    if strategy is CredentialStrategy.MANUAL:
        active = next((item for item in credentials if item.is_active), None)
        return [active] if active else []

    if strategy is CredentialStrategy.FAILOVER:
        active = next((item for item in credentials if item.is_active), None)
        if not active:
            return credentials
        return [active, *(item for item in credentials if item.id != active.id)]

    if not credentials:
        return []
    cursor = policy.round_robin_cursor % len(credentials)
    return [*credentials[cursor:], *credentials[:cursor]]


def _promote_next_active(
    db: Session,
    provider_id: str,
    excluded_id: int,
) -> None:
    replacement = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.provider_id == provider_id,
            ProviderCredential.is_enabled.is_(True),
            ProviderCredential.id != excluded_id,
        )
        .order_by(
            ProviderCredential.priority.asc(),
            ProviderCredential.id.asc(),
        )
        .first()
    )
    if replacement:
        replacement.is_active = True


def _record_success(
    credential: ProviderCredential,
    now: datetime,
) -> None:
    credential.health_status = "healthy"
    credential.consecutive_failures = 0
    credential.cooldown_until = None
    credential.last_used_at = _db_datetime(now)
    credential.updated_at = _db_datetime(now)


def _record_failure(
    db: Session,
    credential: ProviderCredential,
    error: CredentialAttemptError,
    now: datetime,
) -> None:
    credential.consecutive_failures += 1
    credential.updated_at = _db_datetime(now)

    if error.kind is CredentialFailureKind.AUTHENTICATION:
        credential.health_status = "invalid"
        credential.is_enabled = False
        credential.cooldown_until = None
        if credential.is_active:
            credential.is_active = False
            _promote_next_active(db, credential.provider_id, credential.id)
        return

    if error.kind is CredentialFailureKind.RATE_LIMIT:
        retry_after = max(
            float(error.retry_after or DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS),
            1.0,
        )
        credential.health_status = "rate_limited"
        credential.cooldown_until = _db_datetime(
            now + timedelta(seconds=retry_after)
        )
        return

    if error.kind is CredentialFailureKind.TEMPORARY:
        credential.health_status = "degraded"
        credential.cooldown_until = _db_datetime(
            now + timedelta(seconds=DEFAULT_TEMPORARY_COOLDOWN_SECONDS)
        )


def execute_with_credential_rotation(
    db: Session,
    provider_id: str,
    attempt: Callable[[str, int], ResultT],
    *,
    cipher: CredentialCipher | None = None,
    now: datetime | None = None,
) -> ResultT:
    """Execute one operation using the provider's configured credential policy."""
    current_time = now or _utc_now()
    policy = get_credential_policy(db, provider_id)
    eligible = _eligible_credentials(db, provider_id, current_time)
    candidates = _ordered_candidates(eligible, policy)
    if not candidates:
        raise NoEligibleCredentialError(
            "No enabled provider credential is currently available."
        )

    strategy = CredentialStrategy(policy.strategy)
    allowed_attempts = 1 if strategy is CredentialStrategy.MANUAL else policy.max_attempts
    selected_cipher = cipher or get_credential_cipher()
    last_error: CredentialAttemptError | None = None

    for credential in candidates[: min(allowed_attempts, len(candidates))]:
        secret = decrypt_provider_credential(credential, cipher=selected_cipher)
        try:
            result = attempt(secret, credential.id)
        except CredentialAttemptError as error:
            last_error = error
            if error.kind is CredentialFailureKind.NON_RETRYABLE:
                raise
            _record_failure(db, credential, error, current_time)
            db.commit()
            if strategy is CredentialStrategy.MANUAL:
                raise
            continue

        _record_success(credential, current_time)
        if strategy is CredentialStrategy.ROUND_ROBIN and eligible:
            successful_index = next(
                index for index, item in enumerate(eligible) if item.id == credential.id
            )
            policy.round_robin_cursor = (successful_index + 1) % len(eligible)
            policy.updated_at = _db_datetime(current_time)
        db.commit()
        return result

    if last_error is not None:
        raise last_error
    raise NoEligibleCredentialError(
        "No provider credential attempt could be performed."
    )
