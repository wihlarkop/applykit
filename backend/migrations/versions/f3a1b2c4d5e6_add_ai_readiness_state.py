"""add AI readiness state

Revision ID: f3a1b2c4d5e6
Revises: a7e4b2c91f30
Create Date: 2026-08-03 17:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a1b2c4d5e6"
down_revision: str | Sequence[str] | None = "a7e4b2c91f30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("provider_credential") as batch_op:
        batch_op.add_column(
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )

    op.create_table(
        "ai_readiness_test",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("credential_version", sa.Integer(), nullable=True),
        sa.Column("configuration_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("tested_at", sa.DateTime(), nullable=False),
        sa.Column("failure_category", sa.String(length=64), nullable=True),
        sa.Column("public_message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["provider_credential.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_readiness_test_configuration_fingerprint"),
        "ai_readiness_test",
        ["configuration_fingerprint"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ai_readiness_test_configuration_fingerprint"),
        table_name="ai_readiness_test",
    )
    op.drop_table("ai_readiness_test")
    with op.batch_alter_table("provider_credential") as batch_op:
        batch_op.drop_column("version")
