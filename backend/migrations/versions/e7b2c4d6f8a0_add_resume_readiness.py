"""add resume readiness analyses

Revision ID: e7b2c4d6f8a0
Revises: c4a7e9f21b6d
Create Date: 2026-08-07 02:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7b2c4d6f8a0"
down_revision: str | Sequence[str] | None = "c4a7e9f21b6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resume_readiness_analysis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("generated_cv_id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("role_match_analysis_id", sa.Integer(), nullable=True),
        sa.Column("supersedes_analysis_id", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("overall_band", sa.String(length=32), nullable=True),
        sa.Column("parseability_score", sa.Integer(), nullable=True),
        sa.Column("parseability_band", sa.String(length=32), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("quality_band", sa.String(length=32), nullable=True),
        sa.Column("tailoring_score", sa.Integer(), nullable=True),
        sa.Column("tailoring_band", sa.String(length=32), nullable=True),
        sa.Column("hard_gate_code", sa.String(length=64), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("source_profile_snapshot", sa.Text(), nullable=False),
        sa.Column("job_description_snapshot", sa.Text(), nullable=True),
        sa.Column("job_description_hash", sa.String(length=64), nullable=True),
        sa.Column("extraction_json", sa.Text(), nullable=True),
        sa.Column("rules_version", sa.String(length=64), nullable=False),
        sa.Column("extraction_version", sa.String(length=64), nullable=False),
        sa.Column("semantic_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["generated_cv_id"], ["generated_cv.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profile.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["role_match_analysis_id"],
            ["role_match_analysis.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_analysis_id"],
            ["resume_readiness_analysis.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resume_readiness_analysis_generated_cv_id",
        "resume_readiness_analysis",
        ["generated_cv_id"],
        unique=False,
    )
    op.create_index(
        "ix_resume_readiness_analysis_profile_id",
        "resume_readiness_analysis",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_resume_readiness_analysis_role_match_analysis_id",
        "resume_readiness_analysis",
        ["role_match_analysis_id"],
        unique=False,
    )
    op.create_index(
        "ix_resume_readiness_analysis_job_description_hash",
        "resume_readiness_analysis",
        ["job_description_hash"],
        unique=False,
    )

    op.create_table(
        "resume_readiness_rule_result",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("score_delta", sa.Integer(), nullable=False),
        sa.Column("score_cap", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("locations_json", sa.Text(), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["resume_readiness_analysis.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resume_readiness_rule_result_analysis_id",
        "resume_readiness_rule_result",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        "ix_resume_readiness_rule_result_rule_id",
        "resume_readiness_rule_result",
        ["rule_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resume_readiness_rule_result_rule_id",
        table_name="resume_readiness_rule_result",
    )
    op.drop_index(
        "ix_resume_readiness_rule_result_analysis_id",
        table_name="resume_readiness_rule_result",
    )
    op.drop_table("resume_readiness_rule_result")
    op.drop_index(
        "ix_resume_readiness_analysis_job_description_hash",
        table_name="resume_readiness_analysis",
    )
    op.drop_index(
        "ix_resume_readiness_analysis_role_match_analysis_id",
        table_name="resume_readiness_analysis",
    )
    op.drop_index(
        "ix_resume_readiness_analysis_profile_id",
        table_name="resume_readiness_analysis",
    )
    op.drop_index(
        "ix_resume_readiness_analysis_generated_cv_id",
        table_name="resume_readiness_analysis",
    )
    op.drop_table("resume_readiness_analysis")
