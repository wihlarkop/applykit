import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.models import AiReadinessTest, ProviderCredential

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_provider_credentials_have_secret_version() -> None:
    credential = ProviderCredential(
        provider_id="gemini",
        label="Personal",
        encrypted_secret="ciphertext",
        masked_secret="****1234",
        fingerprint="f" * 64,
    )
    assert credential.version in (None, 1)


def test_ai_readiness_test_model_supports_sanitized_result() -> None:
    row = AiReadinessTest(
        id=1,
        provider_id="gemini",
        model_id="gemini/gemini-2.5-flash",
        base_url=None,
        credential_id=7,
        credential_version=1,
        configuration_fingerprint="a" * 64,
        status="success",
        failure_category=None,
        public_message="Connection verified.",
    )
    assert row.id == 1
    assert row.status == "success"


def test_readiness_migration_preserves_existing_credentials(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "readiness-migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    application_logger = logging.getLogger("app.exceptions.handlers")
    application_logger.disabled = False

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "a7e4b2c91f30")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO provider_credential (
                        provider_id, label, encrypted_secret, masked_secret,
                        fingerprint, is_active, is_enabled, priority,
                        health_status, consecutive_failures, created_at, updated_at
                    ) VALUES (
                        'gemini', 'Legacy', 'ciphertext', '****1234',
                        :fingerprint, 1, 1, 1, 'healthy', 0,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {"fingerprint": "f" * 64},
            )
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        credential_columns = {
            column["name"] for column in inspector.get_columns("provider_credential")
        }
        readiness_columns = {
            column["name"] for column in inspector.get_columns("ai_readiness_test")
        }
        assert "version" in credential_columns
        assert {
            "id",
            "provider_id",
            "model_id",
            "base_url",
            "credential_id",
            "credential_version",
            "configuration_fingerprint",
            "status",
            "tested_at",
            "failure_category",
            "public_message",
        } <= readiness_columns
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version FROM provider_credential WHERE label='Legacy'")
            ).scalar_one()
        assert version == 1
    finally:
        engine.dispose()
