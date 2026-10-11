import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from app.schemas import ApplicationStatus

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "migrations/versions/4ac56bd7645a_migrate_offer_status_to_negotiating.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_4ac56bd7645a", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_application_status_no_longer_has_offer():
    assert "offer" not in ApplicationStatus.__members__
    assert {"bookmarked", "applying", "negotiating", "accepted"} <= set(
        ApplicationStatus.__members__
    )


def test_migration_upgrade_moves_offer_rows_to_negotiating():
    migration = _load_migration()
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE application (id INTEGER PRIMARY KEY, status VARCHAR)"))
        conn.execute(
            sa.text(
                "INSERT INTO application (id, status) VALUES "
                "(1, 'offer'), (2, 'applied'), (3, 'offer')"
            )
        )
        conn.commit()

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        with Operations.context(op):
            migration.upgrade()
        conn.commit()

        rows = dict(conn.execute(sa.text("SELECT id, status FROM application")).fetchall())
        assert rows == {1: "negotiating", 2: "applied", 3: "negotiating"}


def test_migration_downgrade_collapses_both_new_stages_back_to_offer():
    migration = _load_migration()
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE application (id INTEGER PRIMARY KEY, status VARCHAR)"))
        conn.execute(
            sa.text(
                "INSERT INTO application (id, status) VALUES "
                "(1, 'negotiating'), (2, 'accepted'), (3, 'applied')"
            )
        )
        conn.commit()

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        with Operations.context(op):
            migration.downgrade()
        conn.commit()

        rows = dict(conn.execute(sa.text("SELECT id, status FROM application")).fetchall())
        assert rows == {1: "offer", 2: "offer", 3: "applied"}
