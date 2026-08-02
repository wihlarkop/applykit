from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.service import (
    AuthenticationLocked,
    authenticate_session,
    change_owner_password,
    complete_owner_setup,
    create_auth_session,
    issue_setup_token,
    record_login_failure,
    record_login_success,
    record_security_event,
    reset_owner_password,
    revoke_other_sessions,
    security_summary,
    verify_owner_password,
)
from app.models import (
    AuthSession,
    AuthSetupToken,
    Base,
    SecurityAuditEvent,
)


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def test_setup_token_is_one_time_hashed_and_expires_after_30_minutes() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        raw_token = issue_setup_token(db, now=now)
        stored = db.scalar(select(AuthSetupToken))

        assert raw_token
        assert stored is not None
        assert stored.token_hash != raw_token
        assert _as_utc(stored.expires_at) == now + timedelta(minutes=30)

        owner = complete_owner_setup(
            db,
            setup_token=raw_token,
            password="correct horse battery staple",
            display_name="Owner",
            now=now + timedelta(minutes=1),
        )

        assert owner.display_name == "Owner"
        assert verify_owner_password(db, "correct horse battery staple") is True
        assert db.scalar(select(AuthSetupToken)) is None
    finally:
        db.close()


def test_setup_token_cannot_be_used_after_expiry() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        raw_token = issue_setup_token(db, now=now)

        try:
            complete_owner_setup(
                db,
                setup_token=raw_token,
                password="correct horse battery staple",
                display_name=None,
                now=now + timedelta(minutes=31),
            )
        except ValueError as exc:
            assert str(exc) == "Setup could not be completed."
        else:
            raise AssertionError("expired setup token should be rejected")
    finally:
        db.close()


def test_session_tokens_are_opaque_and_only_hashes_are_stored() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        setup_token = issue_setup_token(db, now=now)
        complete_owner_setup(
            db,
            setup_token=setup_token,
            password="correct horse battery staple",
            display_name=None,
            now=now,
        )

        issued = create_auth_session(db, remember_device=False, now=now)
        stored = db.scalar(select(AuthSession))

        assert stored is not None
        assert stored.token_hash != issued.session_token
        assert issued.expires_at == now + timedelta(days=7)
        assert authenticate_session(db, issued.session_token, now=now) is not None
        assert (
            authenticate_session(
                db,
                issued.session_token,
                now=now + timedelta(days=7, seconds=1),
            )
            is None
        )
    finally:
        db.close()


def test_remembered_session_has_absolute_30_day_expiry() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        issued = create_auth_session(db, remember_device=True, now=now)

        assert issued.expires_at == now + timedelta(days=30)
        assert authenticate_session(db, issued.session_token, now=now + timedelta(days=29))
        assert (
            authenticate_session(
                db,
                issued.session_token,
                now=now + timedelta(days=30, seconds=1),
            )
            is None
        )
    finally:
        db.close()


def test_change_password_rotates_current_session_and_revokes_others() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        setup_token = issue_setup_token(db, now=now)
        complete_owner_setup(
            db,
            setup_token=setup_token,
            password="correct horse battery staple",
            display_name=None,
            now=now,
        )
        current = create_auth_session(db, remember_device=False, now=now)
        other = create_auth_session(db, remember_device=True, now=now)

        replacement = change_owner_password(
            db,
            current_session_token=current.session_token,
            current_password="correct horse battery staple",
            new_password="a much better passphrase",
            now=now + timedelta(minutes=5),
        )

        assert replacement.session_token != current.session_token
        assert authenticate_session(db, current.session_token, now=now) is None
        assert authenticate_session(db, other.session_token, now=now) is None
        assert authenticate_session(db, replacement.session_token, now=now) is not None
        assert verify_owner_password(db, "a much better passphrase") is True
    finally:
        db.close()


def test_cli_reset_revokes_every_session_and_clears_lockout() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        setup_token = issue_setup_token(db, now=now)
        complete_owner_setup(
            db,
            setup_token=setup_token,
            password="correct horse battery staple",
            display_name=None,
            now=now,
        )
        issued = create_auth_session(db, remember_device=False, now=now)
        for _ in range(5):
            try:
                record_login_failure(db, now=now)
            except AuthenticationLocked:
                pass

        reset_owner_password(db, "replacement passphrase", now=now)

        assert authenticate_session(db, issued.session_token, now=now) is None
        assert verify_owner_password(db, "replacement passphrase") is True
        record_login_success(db, now=now)
    finally:
        db.close()


def test_five_failures_in_ten_minutes_lock_login_for_15_minutes() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        for attempt in range(1, 5):
            record_login_failure(db, now=now + timedelta(minutes=attempt))

        try:
            record_login_failure(db, now=now + timedelta(minutes=5))
        except AuthenticationLocked as exc:
            assert exc.locked_until == now + timedelta(minutes=20)
        else:
            raise AssertionError("fifth failure should lock authentication")

        try:
            record_login_failure(db, now=now + timedelta(minutes=19))
        except AuthenticationLocked:
            pass
        else:
            raise AssertionError("lockout should remain active for 15 minutes")

        record_login_success(db, now=now + timedelta(minutes=21))
    finally:
        db.close()


def test_security_summary_and_revoke_other_sessions() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        current = create_auth_session(db, remember_device=False, now=now)
        create_auth_session(db, remember_device=False, now=now)
        create_auth_session(db, remember_device=True, now=now)

        assert security_summary(db, current.session_token, now=now).other_sessions == 2
        assert revoke_other_sessions(db, current.session_token, now=now) == 2
        assert security_summary(db, current.session_token, now=now).other_sessions == 0
    finally:
        db.close()


def test_security_audit_log_keeps_only_1000_latest_events() -> None:
    db = _make_session()
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    try:
        for index in range(1005):
            record_security_event(
                db,
                "login_failed",
                now=now + timedelta(seconds=index),
            )
        db.commit()

        events = list(
            db.scalars(select(SecurityAuditEvent).order_by(SecurityAuditEvent.id))
        )
        assert len(events) == 1000
        assert _as_utc(events[0].created_at) == now + timedelta(seconds=5)
    finally:
        db.close()
