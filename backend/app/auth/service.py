"""Persistence-backed authentication services for protected Community mode."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password, verify_password
from app.models import (
    AuthLoginState,
    AuthOwner,
    AuthSession,
    AuthSetupToken,
    SecurityAuditEvent,
)

logger = logging.getLogger(__name__)

SETUP_TOKEN_TTL = timedelta(minutes=30)
NORMAL_SESSION_TTL = timedelta(days=7)
REMEMBERED_SESSION_TTL = timedelta(days=30)
LOGIN_WINDOW = timedelta(minutes=10)
LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT = timedelta(minutes=15)
MAX_SECURITY_EVENTS = 1000


class AuthenticationLocked(RuntimeError):
    """Raised while authentication attempts are temporarily locked."""

    def __init__(self, locked_until: datetime):
        self.locked_until = _public_time(locked_until)
        super().__init__("Authentication is temporarily locked.")


class InvalidCredentials(ValueError):
    """Raised for a generic authentication failure."""


class OwnerAlreadyConfigured(RuntimeError):
    """Raised when first-owner setup has already completed."""


class OwnerNotConfigured(RuntimeError):
    """Raised when an owner-only operation runs before setup."""


@dataclass(frozen=True)
class IssuedSession:
    session_token: str
    csrf_token: str
    expires_at: datetime
    remember_device: bool


@dataclass(frozen=True)
class SecuritySummary:
    other_sessions: int


def _now() -> datetime:
    return datetime.now(UTC)


def _db_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _public_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def owner_exists(db: Session) -> bool:
    return db.scalar(select(AuthOwner.id).limit(1)) is not None


def record_security_event(
    db: Session,
    event_type: str,
    *,
    now: datetime | None = None,
) -> None:
    """Write a minimal event and retain only the newest 1,000 records."""
    timestamp = _db_time(now or _now())
    db.add(SecurityAuditEvent(event_type=event_type, created_at=timestamp))
    db.flush()

    stale_ids = list(
        db.scalars(
            select(SecurityAuditEvent.id)
            .order_by(SecurityAuditEvent.id.desc())
            .offset(MAX_SECURITY_EVENTS)
        )
    )
    if stale_ids:
        db.execute(
            delete(SecurityAuditEvent).where(SecurityAuditEvent.id.in_(stale_ids))
        )

    logger.info("Security event: %s", event_type)


def issue_setup_token(db: Session, *, now: datetime | None = None) -> str:
    """Replace any previous setup token and return the new raw value once."""
    timestamp = now or _now()
    raw_token = secrets.token_urlsafe(32)
    db.execute(delete(AuthSetupToken))
    db.add(
        AuthSetupToken(
            id=1,
            token_hash=hash_token(raw_token),
            created_at=_db_time(timestamp),
            expires_at=_db_time(timestamp + SETUP_TOKEN_TTL),
        )
    )
    db.commit()
    return raw_token


def complete_owner_setup(
    db: Session,
    *,
    setup_token: str,
    password: str,
    display_name: str | None,
    now: datetime | None = None,
) -> AuthOwner:
    """Consume a valid setup token and create the installation owner."""
    if owner_exists(db):
        raise OwnerAlreadyConfigured("Owner setup is already complete.")

    timestamp = now or _now()
    stored = db.scalar(select(AuthSetupToken).limit(1))
    token_valid = bool(
        stored
        and stored.expires_at > _db_time(timestamp)
        and hmac.compare_digest(stored.token_hash, hash_token(setup_token))
    )
    if not token_valid:
        raise ValueError("Setup could not be completed.")

    owner = AuthOwner(
        id=1,
        display_name=(display_name or "").strip() or None,
        password_hash=hash_password(password),
        created_at=_db_time(timestamp),
        password_changed_at=_db_time(timestamp),
    )
    db.add(owner)
    db.execute(delete(AuthSetupToken))
    record_security_event(db, "owner_setup_completed", now=timestamp)
    db.commit()
    db.refresh(owner)
    return owner


def verify_owner_password(db: Session, password: str) -> bool:
    owner = db.scalar(select(AuthOwner).limit(1))
    if owner is None:
        return False

    verified, upgraded_hash = verify_password(password, owner.password_hash)
    if verified and upgraded_hash:
        owner.password_hash = upgraded_hash
        db.commit()
    return verified


def create_auth_session(
    db: Session,
    *,
    remember_device: bool,
    now: datetime | None = None,
) -> IssuedSession:
    timestamp = now or _now()
    expires_at = timestamp + (
        REMEMBERED_SESSION_TTL if remember_device else NORMAL_SESSION_TTL
    )
    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=hash_token(session_token),
            csrf_token_hash=hash_token(csrf_token),
            remember_device=remember_device,
            created_at=_db_time(timestamp),
            expires_at=_db_time(expires_at),
        )
    )
    db.commit()
    return IssuedSession(
        session_token=session_token,
        csrf_token=csrf_token,
        expires_at=_public_time(expires_at),
        remember_device=remember_device,
    )


def authenticate_session(
    db: Session,
    session_token: str | None,
    *,
    now: datetime | None = None,
) -> AuthSession | None:
    if not session_token:
        return None

    timestamp = _db_time(now or _now())
    stored = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(session_token))
    )
    if stored is None or stored.revoked_at is not None:
        return None
    if stored.expires_at <= timestamp:
        db.delete(stored)
        db.commit()
        return None
    return stored


def validate_csrf_token(session: AuthSession, csrf_token: str | None) -> bool:
    if not csrf_token:
        return False
    return hmac.compare_digest(session.csrf_token_hash, hash_token(csrf_token))


def revoke_session(
    db: Session,
    session_token: str | None,
    *,
    now: datetime | None = None,
) -> bool:
    stored = authenticate_session(db, session_token, now=now)
    if stored is None:
        return False
    stored.revoked_at = _db_time(now or _now())
    record_security_event(db, "logout", now=now)
    db.commit()
    return True


def _revoke_all_sessions(db: Session, *, now: datetime) -> None:
    active = list(
        db.scalars(select(AuthSession).where(AuthSession.revoked_at.is_(None)))
    )
    for session in active:
        session.revoked_at = _db_time(now)


def change_owner_password(
    db: Session,
    *,
    current_session_token: str,
    current_password: str,
    new_password: str,
    now: datetime | None = None,
) -> IssuedSession:
    timestamp = now or _now()
    current_session = authenticate_session(db, current_session_token, now=timestamp)
    owner = db.scalar(select(AuthOwner).limit(1))
    if current_session is None or owner is None:
        raise InvalidCredentials("Password could not be changed.")

    verified, _ = verify_password(current_password, owner.password_hash)
    if not verified:
        raise InvalidCredentials("Password could not be changed.")

    remember_device = bool(current_session.remember_device)
    owner.password_hash = hash_password(new_password)
    owner.password_changed_at = _db_time(timestamp)
    _revoke_all_sessions(db, now=timestamp)
    record_security_event(db, "password_changed", now=timestamp)
    db.commit()
    return create_auth_session(
        db,
        remember_device=remember_device,
        now=timestamp,
    )


def reset_owner_password(
    db: Session,
    new_password: str,
    *,
    now: datetime | None = None,
) -> None:
    timestamp = now or _now()
    owner = db.scalar(select(AuthOwner).limit(1))
    if owner is None:
        raise OwnerNotConfigured("Owner setup has not been completed.")

    owner.password_hash = hash_password(new_password)
    owner.password_changed_at = _db_time(timestamp)
    _revoke_all_sessions(db, now=timestamp)
    state = db.get(AuthLoginState, 1)
    if state is not None:
        state.failed_count = 0
        state.window_started_at = None
        state.locked_until = None
    record_security_event(db, "password_reset_cli", now=timestamp)
    db.commit()


def _login_state(db: Session) -> AuthLoginState:
    state = db.get(AuthLoginState, 1)
    if state is None:
        state = AuthLoginState(id=1, failed_count=0)
        db.add(state)
        db.flush()
    return state


def check_authentication_allowed(
    db: Session,
    *,
    now: datetime | None = None,
) -> None:
    timestamp = _db_time(now or _now())
    state = _login_state(db)
    if state.locked_until and state.locked_until > timestamp:
        raise AuthenticationLocked(state.locked_until)
    if state.locked_until and state.locked_until <= timestamp:
        state.failed_count = 0
        state.window_started_at = None
        state.locked_until = None
        db.commit()


def record_login_failure(
    db: Session,
    *,
    now: datetime | None = None,
) -> None:
    timestamp = _db_time(now or _now())
    state = _login_state(db)
    if state.locked_until and state.locked_until > timestamp:
        raise AuthenticationLocked(state.locked_until)

    if (
        state.window_started_at is None
        or timestamp - state.window_started_at >= LOGIN_WINDOW
    ):
        state.failed_count = 0
        state.window_started_at = timestamp
        state.locked_until = None

    state.failed_count += 1
    record_security_event(db, "login_failed", now=timestamp)
    if state.failed_count >= LOGIN_MAX_FAILURES:
        state.locked_until = timestamp + LOGIN_LOCKOUT
        record_security_event(db, "login_lockout_started", now=timestamp)
        db.commit()
        raise AuthenticationLocked(state.locked_until)
    db.commit()


def record_login_success(
    db: Session,
    *,
    now: datetime | None = None,
) -> None:
    timestamp = now or _now()
    state = _login_state(db)
    state.failed_count = 0
    state.window_started_at = None
    state.locked_until = None
    record_security_event(db, "login_succeeded", now=timestamp)
    db.commit()


def security_summary(
    db: Session,
    current_session_token: str,
    *,
    now: datetime | None = None,
) -> SecuritySummary:
    timestamp = _db_time(now or _now())
    current = authenticate_session(db, current_session_token, now=timestamp)
    if current is None:
        raise InvalidCredentials("Authentication required.")

    count = db.scalar(
        select(func.count(AuthSession.id)).where(
            AuthSession.id != current.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > timestamp,
        )
    )
    return SecuritySummary(other_sessions=int(count or 0))


def revoke_other_sessions(
    db: Session,
    current_session_token: str,
    *,
    now: datetime | None = None,
) -> int:
    timestamp = now or _now()
    current = authenticate_session(db, current_session_token, now=timestamp)
    if current is None:
        raise InvalidCredentials("Authentication required.")

    others = list(
        db.scalars(
            select(AuthSession).where(
                AuthSession.id != current.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > _db_time(timestamp),
            )
        )
    )
    for session in others:
        session.revoked_at = _db_time(timestamp)
    record_security_event(db, "other_sessions_revoked", now=timestamp)
    db.commit()
    return len(others)
