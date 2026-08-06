"""link cover letters to role match analyses

Revision ID: d9f4a2c7e1b3
Revises: c4a7e9f21b6d
Create Date: 2026-08-06 14:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9f4a2c7e1b3"
down_revision: str | Sequence[str] | None = "c4a7e9f21b6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("generated_cover_letter") as batch_op:
        batch_op.add_column(
            sa.Column("role_match_analysis_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_generated_cover_letter_role_match_analysis_id",
            "role_match_analysis",
            ["role_match_analysis_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_generated_cover_letter_role_match_analysis_id",
            ["role_match_analysis_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("generated_cover_letter") as batch_op:
        batch_op.drop_index("ix_generated_cover_letter_role_match_analysis_id")
        batch_op.drop_constraint(
            "fk_generated_cover_letter_role_match_analysis_id",
            type_="foreignkey",
        )
        batch_op.drop_column("role_match_analysis_id")
