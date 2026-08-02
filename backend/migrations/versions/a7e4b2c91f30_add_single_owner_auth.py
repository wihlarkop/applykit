"""add single owner auth

Revision ID: a7e4b2c91f30
Revises: 91c5d1e2a7b4
Create Date: 2026-08-02 17:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7e4b2c91f30"
down_revision: str | Sequence[str] | None = "91c5d1e2a7b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_owner",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "auth_session",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("remember_device", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sqlite_autoincrement=True,
    )
    op.create_index(
        op.f("ix_auth_session_expires_at"),
        "auth_session",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_auth_session_revoked_at"),
        "auth_session",
        ["revoked_at"],
        unique=False,
    )

    op.create_table(
        "auth_setup_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )

    op.create_table(
        "auth_login_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(), nullable=True),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "security_audit_event",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_security_audit_event_event_type"),
        "security_audit_event",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_security_audit_event_event_type"),
        table_name="security_audit_event",
    )
    op.drop_table("security_audit_event")
    op.drop_table("auth_login_state")
    op.drop_table("auth_setup_token")
    op.drop_index(op.f("ix_auth_session_revoked_at"), table_name="auth_session")
    op.drop_index(op.f("ix_auth_session_expires_at"), table_name="auth_session")
    op.drop_table("auth_session")
    op.drop_table("auth_owner")
