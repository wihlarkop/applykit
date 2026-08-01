"""add provider credential vault

Revision ID: 91c5d1e2a7b4
Revises: 1284f7500697
Create Date: 2026-08-02 05:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "91c5d1e2a7b4"
down_revision: str | Sequence[str] | None = "1284f7500697"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_credential",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("masked_secret", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("health_status", sa.String(length=32), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("cooldown_until", sa.DateTime(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_id",
            "fingerprint",
            name="uq_provider_credential_fingerprint",
        ),
    )
    op.create_index(
        op.f("ix_provider_credential_provider_id"),
        "provider_credential",
        ["provider_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_provider_credential_is_active"),
        "provider_credential",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "provider_credential_policy",
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("strategy", sa.String(length=32), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("round_robin_cursor", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("provider_id"),
    )


def downgrade() -> None:
    op.drop_table("provider_credential_policy")
    op.drop_index(
        op.f("ix_provider_credential_is_active"),
        table_name="provider_credential",
    )
    op.drop_index(
        op.f("ix_provider_credential_provider_id"),
        table_name="provider_credential",
    )
    op.drop_table("provider_credential")
