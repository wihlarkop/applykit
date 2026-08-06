"""add role match analysis snapshots

Revision ID: c4a7e9f21b6d
Revises: f3a1b2c4d5e6
Create Date: 2026-08-06 08:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4a7e9f21b6d"
down_revision: str | Sequence[str] | None = "f3a1b2c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "role_match_analysis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_analysis_id", sa.Integer(), nullable=True),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("job_description_hash", sa.String(length=64), nullable=False),
        sa.Column("safe_profile_snapshot", sa.Text(), nullable=False),
        sa.Column("safe_profile_hash", sa.String(length=64), nullable=False),
        sa.Column("rules_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("model_provider", sa.String(length=255), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("raw_llm_output", sa.Text(), nullable=True),
        sa.Column("normalized_payload", sa.Text(), nullable=True),
        sa.Column("scoring_payload", sa.Text(), nullable=True),
        sa.Column("raw_score", sa.Float(), nullable=True),
        sa.Column("display_score", sa.Integer(), nullable=True),
        sa.Column("score_band", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("confidence_band", sa.String(length=32), nullable=True),
        sa.Column("eligibility_status", sa.String(length=32), nullable=False),
        sa.Column("show_authoritative_score", sa.Boolean(), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("excluded_items", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_analysis_id"], ["role_match_analysis.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["profile_id"], ["profile.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["role_match_analysis.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_role_match_analysis_job_description_hash", "role_match_analysis", ["job_description_hash"], unique=False)
    op.create_index("ix_role_match_analysis_safe_profile_hash", "role_match_analysis", ["safe_profile_hash"], unique=False)

    op.create_table(
        "role_match_requirement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("cluster_id", sa.String(length=255), nullable=False),
        sa.Column("canonical_key", sa.String(length=255), nullable=False),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("primary_category", sa.String(length=64), nullable=False),
        sa.Column("extracted_importance", sa.String(length=32), nullable=False),
        sa.Column("effective_importance", sa.String(length=32), nullable=False),
        sa.Column("mention_count", sa.Integer(), nullable=False),
        sa.Column("importance_conflict", sa.Boolean(), nullable=False),
        sa.Column("importance_mentions", sa.Text(), nullable=False),
        sa.Column("source_quotes", sa.Text(), nullable=False),
        sa.Column("volatility", sa.String(length=32), nullable=False),
        sa.Column("minimum_months", sa.Integer(), nullable=True),
        sa.Column("tool_specificity", sa.String(length=32), nullable=False),
        sa.Column("excluded", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("match_level", sa.String(length=32), nullable=True),
        sa.Column("strength", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["role_match_analysis.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_role_match_requirement_analysis_id", "role_match_requirement", ["analysis_id"], unique=False)

    op.create_table(
        "role_match_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("relationship", sa.String(length=64), nullable=False),
        sa.Column("depth", sa.String(length=64), nullable=False),
        sa.Column("recency_multiplier", sa.Float(), nullable=False),
        sa.Column("base_strength", sa.Float(), nullable=False),
        sa.Column("duplicate", sa.Boolean(), nullable=False),
        sa.Column("contradiction", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["role_match_analysis.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requirement_id"], ["role_match_requirement.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_role_match_evidence_analysis_id", "role_match_evidence", ["analysis_id"], unique=False)
    op.create_index("ix_role_match_evidence_requirement_id", "role_match_evidence", ["requirement_id"], unique=False)

    op.create_table(
        "role_match_override",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("requirement_key", sa.String(length=255), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("extracted_value", sa.Text(), nullable=True),
        sa.Column("effective_value", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("carry_status", sa.String(length=32), nullable=False),
        sa.Column("source_override_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["role_match_analysis.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_override_id"], ["role_match_override.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_role_match_override_analysis_id", "role_match_override", ["analysis_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_role_match_override_analysis_id", table_name="role_match_override")
    op.drop_table("role_match_override")
    op.drop_index("ix_role_match_evidence_requirement_id", table_name="role_match_evidence")
    op.drop_index("ix_role_match_evidence_analysis_id", table_name="role_match_evidence")
    op.drop_table("role_match_evidence")
    op.drop_index("ix_role_match_requirement_analysis_id", table_name="role_match_requirement")
    op.drop_table("role_match_requirement")
    op.drop_index("ix_role_match_analysis_safe_profile_hash", table_name="role_match_analysis")
    op.drop_index("ix_role_match_analysis_job_description_hash", table_name="role_match_analysis")
    op.drop_table("role_match_analysis")
