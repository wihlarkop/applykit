import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "migrations/versions/528ea0bbfe26_add_salary_range_excitement_and_date_.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "migration_528ea0bbfe26", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_and_downgrade_preserve_existing_free_text_salary_values():
    migration = _load_migration()
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(
            sa.text("CREATE TABLE application (id INTEGER PRIMARY KEY, salary VARCHAR)")
        )
        conn.execute(
            sa.text(
                "INSERT INTO application (id, salary) VALUES "
                "(1, 'Competitive'), (2, '$120K-$150K'), (3, NULL)"
            )
        )
        conn.commit()

        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            migration.upgrade()
        conn.commit()

        rows = dict(
            conn.execute(sa.text("SELECT id, salary FROM application")).fetchall()
        )
        assert rows == {1: "Competitive", 2: "$120K-$150K", 3: None}

        with Operations.context(ctx):
            migration.downgrade()
        conn.commit()

        rows = dict(
            conn.execute(sa.text("SELECT id, salary FROM application")).fetchall()
        )
        assert rows == {1: "Competitive", 2: "$120K-$150K", 3: None}
