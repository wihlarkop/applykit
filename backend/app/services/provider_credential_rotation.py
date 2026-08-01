"""Credential strategy selection and bounded provider-key rotation."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ResolvedCredentialAttempt:
    credential_id: int
    secret: str


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _db_datetime(value: datetime) -> datetime:
    """SQLite persists UTC timestamps without timezone metadata."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _status_code(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(error, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _retry_after(error: Exception) -> float | None:
    direct = getattr(error, "retry_after", None)
    if isinstance(direct, int | float):
        return float(direct)

    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        value = headers.get("retry-after") or headers.get("Retry-After")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            pass

    message = str(error)
    for pattern in (
        r"retry[_\s]delay[\":\s]+(\d+(?:\.\d+)?)",
        r"retry in (\d+(?:\.\d+)?)s",
    ):
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def classify_provider_exception(error: Exception) -> CredentialAttemptError:
    """Map provider exceptions to the limited set of safe rotation decisions."""
    status = _status_code(error)
    name = type(error).__name__.lower()

    if status in {401, 403} or any(
        marker in name
        for marker in ("authentication", "permissiondenied", "unauthorized")
    ):
        kind = CredentialFailureKind.AUTHENTICATION
    elif status == 429 or "ratelimit" in name:
        kind = CredentialFailureKind.RATE_LIMIT
    elif (status is not None and 500 <= status <= 599) or any(
        marker in name
        for marker in (
            "serviceunavailable",
            "apiconnection",
            "timeout",
            "internalserver",
        )
    ):
        kind = CredentialFailureKind.TEMPORARY
    else:
        kind = CredentialFailureKind.NON_RETRYABLE

    return CredentialAttemptError(
        kind,
        retry_after=_retry_after(error),
        original=error,
    )


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


class CredentialRotationPlan:
    """Reusable rotation state for synchronous and streaming operations."""

    def __init__(
        self,
        db: Session,
        provider_id: str,
        *,
        cipher: CredentialCipher | None = None,
        now: datetime | None = None,
    ) -> None:
        self.db = db
        self.provider_id = provider_id
        self.now = now or _utc_now()
        self.policy = get_credential_policy(db, provider_id)
        self.strategy = CredentialStrategy(self.policy.strategy)
        self.eligible = _eligible_credentials(db, provider_id, self.now)
        candidates = _ordered_candidates(self.eligible, self.policy)
        allowed_attempts = (
            1 if self.strategy is CredentialStrategy.MANUAL else self.policy.max_attempts
        )
        self.candidates = candidates[: min(allowed_attempts, len(candidates))]
        self.cipher = cipher or get_credential_cipher()

        if not self.candidates:
            raise NoEligibleCredentialError(
                "No enabled provider credential is currently available."
            )

    def attempts(self) -> Iterator[ResolvedCredentialAttempt]:
        for credential in self.candidates:
            yield ResolvedCredentialAttempt(
                credential_id=credential.id,
                secret=decrypt_provider_credential(credential, cipher=self.cipher),
            )

    def _credential(self, credential_id: int) -> ProviderCredential:
        credential = next(
            (item for item in self.candidates if item.id == credential_id),
            None,
        )
        if credential is None:
            raise NoEligibleCredentialError("Credential is not part of this rotation plan.")
        return credential

    def record_failure(
        self,
        credential_id: int,
        error: CredentialAttemptError,
    ) -> None:
        if error.kind is CredentialFailureKind.NON_RETRYABLE:
            return
        _record_failure(self.db, self._credential(credential_id), error, self.now)
        self.db.commit()

    def record_success(self, credential_id: int) -> None:
        credential = self._credential(credential_id)
        _record_success(credential, self.now)
        if self.strategy is CredentialStrategy.ROUND_ROBIN and self.eligible:
            successful_index = next(
                index
                for index, item in enumerate(self.eligible)
                if item.id == credential.id
            )
            self.policy.round_robin_cursor = (successful_index + 1) % len(
                self.eligible
            )
            self.policy.updated_at = _db_datetime(self.now)
        self.db.commit()


def execute_with_credential_rotation(
    db: Session,
    provider_id: str,
    attempt: Callable[[str, int], ResultT],
    *,
    cipher: CredentialCipher | None = None,
    now: datetime | None = None,
) -> ResultT:
    """Execute one operation using the provider's configured credential policy."""
    plan = CredentialRotationPlan(
        db,
        provider_id,
        cipher=cipher,
        now=now,
    )
    last_error: CredentialAttemptError | None = None

    for resolved in plan.attempts():
        try:
            result = attempt(resolved.secret, resolved.credential_id)
        except CredentialAttemptError as error:
            last_error = error
            if error.kind is CredentialFailureKind.NON_RETRYABLE:
                raise
            plan.record_failure(resolved.credential_id, error)
            if plan.strategy is CredentialStrategy.MANUAL:
                raise
            continue

        plan.record_success(resolved.credential_id)
        return result

    if last_error is not None:
        raise last_error
    raise NoEligibleCredentialError(
        "No provider credential attempt could be performed."
    )
