"""support_multiple_github_links_on_profile

Revision ID: f24b8ab225da
Revises: 4ac56bd7645a
Create Date: 2026-09-01 13:55:34.892786

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f24b8ab225da'
down_revision: Union[str, Sequence[str], None] = 'd9f4a2c7e1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_profile = sa.table(
    "profile",
    sa.column("id", sa.Integer),
    sa.column("github", sa.Text),
)


def upgrade() -> None:
    """Upgrade schema.

    github moves from a single string column to a JSON-array-encoded Text
    column (same storage pattern already used for education/skills/etc.),
    so a profile can list more than one GitHub account. Existing plain
    string values are wrapped as a one-item array; empty/null becomes [].
    A value that already parses as a JSON array of strings is left as-is
    rather than wrapped again - some rows were already storing that shape.
    """
    connection = op.get_bind()
    rows = connection.execute(sa.select(_profile.c.id, _profile.c.github)).fetchall()
    for row in rows:
        value = (row.github or "").strip()
        if not value:
            encoded = json.dumps([])
        else:
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                encoded = json.dumps(parsed)
            else:
                encoded = json.dumps([value])
        connection.execute(
            _profile.update().where(_profile.c.id == row.id).values(github=encoded)
        )


def downgrade() -> None:
    """Downgrade schema.

    Collapses back to a single string: the first link in the list, or null
    if the list held zero or more than one entry - any second account is
    unavoidably lost on downgrade.
    """
    connection = op.get_bind()
    rows = connection.execute(sa.select(_profile.c.id, _profile.c.github)).fetchall()
    for row in rows:
        try:
            parsed = json.loads(row.github or "[]")
        except (TypeError, ValueError):
            parsed = []
        value = parsed[0] if isinstance(parsed, list) and len(parsed) == 1 else None
        connection.execute(
            _profile.update().where(_profile.c.id == row.id).values(github=value)
        )
