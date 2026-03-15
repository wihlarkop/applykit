"""add app settings table

Revision ID: d89ac2dc3096
Revises: 574a3faf36f1
Create Date: 2026-03-15 21:18:23.692893

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d89ac2dc3096"
down_revision: str | Sequence[str] | None = "574a3faf36f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "app_setting",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    # Seed default LLM model (user still needs to provide their own API key)
    op.execute(
        "INSERT INTO app_setting (key, value) VALUES ('llm_provider', 'gemini/gemini-2.5-flash')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("app_setting")
