from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.services.credential_crypto import CredentialCipher
from app.services.provider_credential_vault import create_provider_credential
from app.services.provider_credential_rotation import (
    CredentialAttemptError,
    CredentialFailureKind,
    CredentialStrategy,
    NoEligibleCredentialError,
    execute_with_credential_rotation,
    get_credential_policy,
    update_credential_policy,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _cipher() -> CredentialCipher:
    return CredentialCipher(Fernet.generate_key().decode())


def _add_credentials(db, cipher):
    first = create_provider_credential(
        db,
        provider_id="openai",
        label="Primary",
        secret="sk-primary",
        cipher=cipher,
        activate=True,
    )
    second = create_provider_credential(
        db,
        provider_id="openai",
        label="Backup",
        secret="sk-backup",
        cipher=cipher,
        activate=False,
    )
    third = create_provider_credential(
        db,
        provider_id="openai",
        label="Third",
        secret="sk-third",
        cipher=cipher,
        activate=False,
    )
    return first, second, third


def test_manual_strategy_uses_only_the_active_credential():
    db = _make_session()
    cipher = _cipher()
    try:
        _add_credentials(db, cipher)
        update_credential_policy(
            db,
            "openai",
            strategy=CredentialStrategy.MANUAL,
            max_attempts=3,
        )
        attempted: list[str] = []

        def attempt(secret: str, _credential_id: int) -> str:
            attempted.append(secret)
            raise CredentialAttemptError(CredentialFailureKind.RATE_LIMIT, retry_after=30)

        try:
            execute_with_credential_rotation(
                db,
                "openai",
                attempt,
                cipher=cipher,
            )
        except CredentialAttemptError:
            pass
        else:
            raise AssertionError("manual strategy should surface the active-key failure")

        assert attempted == ["sk-primary"]
    finally:
        db.close()


def test_failover_disables_invalid_key_and_promotes_the_next_credential():
    db = _make_session()
    cipher = _cipher()
    try:
        primary, backup, _ = _add_credentials(db, cipher)
        update_credential_policy(
            db,
            "openai",
            strategy=CredentialStrategy.FAILOVER,
            max_attempts=2,
        )
        attempted: list[str] = []

        def attempt(secret: str, _credential_id: int) -> str:
            attempted.append(secret)
            if secret == "sk-primary":
                raise CredentialAttemptError(CredentialFailureKind.AUTHENTICATION)
            return "ok"

        result = execute_with_credential_rotation(
            db,
            "openai",
            attempt,
            cipher=cipher,
        )

        db.refresh(primary)
        db.refresh(backup)
        assert result == "ok"
        assert attempted == ["sk-primary", "sk-backup"]
        assert primary.is_enabled is False
        assert primary.is_active is False
        assert backup.is_active is True
        assert backup.health_status == "healthy"
    finally:
        db.close()


def test_failover_places_rate_limited_key_in_cooldown_without_disabling_it():
    db = _make_session()
    cipher = _cipher()
    now = datetime(2026, 8, 2, 1, 0, tzinfo=UTC)
    persisted_now = now.replace(tzinfo=None)
    try:
        primary, backup, _ = _add_credentials(db, cipher)
        update_credential_policy(
            db,
            "openai",
            strategy=CredentialStrategy.FAILOVER,
            max_attempts=2,
        )

        def attempt(secret: str, _credential_id: int) -> str:
            if secret == "sk-primary":
                raise CredentialAttemptError(
                    CredentialFailureKind.RATE_LIMIT,
                    retry_after=45,
                )
            return "ok"

        assert execute_with_credential_rotation(
            db,
            "openai",
            attempt,
            cipher=cipher,
            now=now,
        ) == "ok"

        db.refresh(primary)
        db.refresh(backup)
        assert primary.is_enabled is True
        assert primary.is_active is True
        assert primary.health_status == "rate_limited"
        assert primary.cooldown_until == persisted_now + timedelta(seconds=45)
        assert backup.last_used_at == persisted_now
    finally:
        db.close()


def test_non_retryable_failure_never_rotates_to_another_key():
    db = _make_session()
    cipher = _cipher()
    try:
        _add_credentials(db, cipher)
        update_credential_policy(
            db,
            "openai",
            strategy=CredentialStrategy.FAILOVER,
            max_attempts=3,
        )
        attempted: list[str] = []

        def attempt(secret: str, _credential_id: int) -> str:
            attempted.append(secret)
            raise CredentialAttemptError(CredentialFailureKind.NON_RETRYABLE)

        try:
            execute_with_credential_rotation(
                db,
                "openai",
                attempt,
                cipher=cipher,
            )
        except CredentialAttemptError as exc:
            assert exc.kind is CredentialFailureKind.NON_RETRYABLE
        else:
            raise AssertionError("non-retryable failure should be surfaced")

        assert attempted == ["sk-primary"]
    finally:
        db.close()


def test_round_robin_cycles_through_eligible_credentials_across_requests():
    db = _make_session()
    cipher = _cipher()
    try:
        _add_credentials(db, cipher)
        update_credential_policy(
            db,
            "openai",
            strategy=CredentialStrategy.ROUND_ROBIN,
            max_attempts=2,
        )
        selected: list[str] = []

        def attempt(secret: str, _credential_id: int) -> str:
            selected.append(secret)
            return secret

        for _ in range(4):
            execute_with_credential_rotation(
                db,
                "openai",
                attempt,
                cipher=cipher,
            )

        assert selected == [
            "sk-primary",
            "sk-backup",
            "sk-third",
            "sk-primary",
        ]
        assert get_credential_policy(db, "openai").round_robin_cursor == 1
    finally:
        db.close()


def test_cooldown_and_disabled_credentials_are_skipped():
    db = _make_session()
    cipher = _cipher()
    now = datetime(2026, 8, 2, 1, 0, tzinfo=UTC)
    try:
        primary, backup, third = _add_credentials(db, cipher)
        primary.cooldown_until = (now + timedelta(minutes=5)).replace(tzinfo=None)
        backup.is_enabled = False
        db.commit()
        update_credential_policy(
            db,
            "openai",
            strategy=CredentialStrategy.FAILOVER,
            max_attempts=3,
        )

        selected: list[int] = []

        result = execute_with_credential_rotation(
            db,
            "openai",
            lambda _secret, credential_id: selected.append(credential_id) or "ok",
            cipher=cipher,
            now=now,
        )

        assert result == "ok"
        assert selected == [third.id]
    finally:
        db.close()


def test_no_eligible_credentials_has_a_typed_failure():
    db = _make_session()
    cipher = _cipher()
    now = datetime(2026, 8, 2, 1, 0, tzinfo=UTC)
    try:
        primary, backup, third = _add_credentials(db, cipher)
        for credential in (primary, backup, third):
            credential.is_enabled = False
        db.commit()

        try:
            execute_with_credential_rotation(
                db,
                "openai",
                lambda _secret, _credential_id: "unexpected",
                cipher=cipher,
                now=now,
            )
        except NoEligibleCredentialError:
            pass
        else:
            raise AssertionError("missing eligible credentials should fail clearly")
    finally:
        db.close()
