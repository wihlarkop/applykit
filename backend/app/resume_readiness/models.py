from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models import Base


class ResumeReadinessAnalysis(Base):
    __tablename__ = "resume_readiness_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_cv_id = Column(
        Integer,
        ForeignKey("generated_cv.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        Integer,
        ForeignKey("profile.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role_match_analysis_id = Column(
        Integer,
        ForeignKey("role_match_analysis.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supersedes_analysis_id = Column(
        Integer,
        ForeignKey("resume_readiness_analysis.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    overall_score = Column(Integer, nullable=True)
    overall_band = Column(String(32), nullable=True)
    parseability_score = Column(Integer, nullable=True)
    parseability_band = Column(String(32), nullable=True)
    quality_score = Column(Integer, nullable=True)
    quality_band = Column(String(32), nullable=True)
    tailoring_score = Column(Integer, nullable=True)
    tailoring_band = Column(String(32), nullable=True)
    hard_gate_code = Column(String(64), nullable=True)
    failure_code = Column(String(64), nullable=True)
    source_profile_snapshot = Column(Text, nullable=False)
    job_description_snapshot = Column(Text, nullable=True)
    job_description_hash = Column(String(64), nullable=True, index=True)
    extraction_json = Column(Text, nullable=True)
    rules_version = Column(String(64), nullable=False)
    extraction_version = Column(String(64), nullable=False)
    semantic_version = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    rule_results = relationship(
        "ResumeReadinessRuleResult",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ResumeReadinessRuleResult.id",
    )


class ResumeReadinessRuleResult(Base):
    __tablename__ = "resume_readiness_rule_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(
        Integer,
        ForeignKey("resume_readiness_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(String(64), nullable=False, index=True)
    category = Column(String(32), nullable=False)
    severity = Column(String(32), nullable=False)
    outcome = Column(String(32), nullable=False)
    score_delta = Column(Integer, nullable=False, default=0)
    score_cap = Column(Integer, nullable=True)
    title = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=False, default="{}")
    locations_json = Column(Text, nullable=False, default="[]")
    requires_review = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
