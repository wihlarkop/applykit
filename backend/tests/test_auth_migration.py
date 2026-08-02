import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]
AUTH_TABLES = {
    "auth_owner",
    "auth_session",
    "auth_setup_token",
    "auth_login_state",
    "security_audit_event",
}


def test_auth_migration_upgrades_and_downgrades_cleanly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "auth-migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    application_logger = logging.getLogger("app.exceptions.handlers")
    application_logger.disabled = False

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    assert application_logger.disabled is False

    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert AUTH_TABLES <= tables
    finally:
        engine.dispose()

    command.downgrade(config, "91c5d1e2a7b4")

    assert application_logger.disabled is False

    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert AUTH_TABLES.isdisjoint(tables)
    finally:
        engine.dispose()
