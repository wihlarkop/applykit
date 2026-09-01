import importlib.util
import json
from pathlib import Path

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "migrations/versions/f24b8ab225da_support_multiple_github_links_on_profile.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_f24b8ab225da", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fresh_connection():
    engine = sa.create_engine("sqlite:///:memory:")
    conn = engine.connect()
    conn.execute(sa.text("CREATE TABLE profile (id INTEGER PRIMARY KEY, github VARCHAR)"))
    return conn


def test_migration_upgrade_wraps_existing_values_as_single_item_arrays():
    migration = _load_migration()
    with _fresh_connection() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO profile (id, github) VALUES "
                "(1, 'https://github.com/alice'), (2, NULL), (3, '')"
            )
        )
        conn.commit()

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        with Operations.context(op):
            migration.upgrade()
        conn.commit()

        rows = dict(conn.execute(sa.text("SELECT id, github FROM profile")).fetchall())
        assert json.loads(rows[1]) == ["https://github.com/alice"]
        assert json.loads(rows[2]) == []
        assert json.loads(rows[3]) == []


def test_migration_upgrade_does_not_double_encode_an_already_json_array_value():
    """Some rows already had a JSON-array string stuffed into the plain
    github column before this migration existed - upgrading must detect
    that shape and use it as-is instead of wrapping it in another array."""
    migration = _load_migration()
    with _fresh_connection() as conn:
        already_encoded = json.dumps(
            ["https://github.com/personal", "https://github.com/work"]
        )
        conn.execute(
            sa.text("INSERT INTO profile (id, github) VALUES (1, :value)"),
            {"value": already_encoded},
        )
        conn.commit()

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        with Operations.context(op):
            migration.upgrade()
        conn.commit()

        rows = dict(conn.execute(sa.text("SELECT id, github FROM profile")).fetchall())
        assert json.loads(rows[1]) == [
            "https://github.com/personal",
            "https://github.com/work",
        ]


def test_migration_downgrade_collapses_single_entry_back_to_a_string():
    migration = _load_migration()
    with _fresh_connection() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO profile (id, github) VALUES "
                "(1, :one), (2, :empty), (3, :two)"
            ),
            {
                "one": json.dumps(["https://github.com/alice"]),
                "empty": json.dumps([]),
                "two": json.dumps(["https://github.com/alice", "https://github.com/alice-work"]),
            },
        )
        conn.commit()

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        with Operations.context(op):
            migration.downgrade()
        conn.commit()

        rows = dict(conn.execute(sa.text("SELECT id, github FROM profile")).fetchall())
        assert rows[1] == "https://github.com/alice"
        assert rows[2] is None
        # Downgrading a profile with two links can't preserve both - it's
        # unavoidably lost, landing on null rather than silently picking one.
        assert rows[3] is None
