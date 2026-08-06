from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text

from app.models import Base, GeneratedCoverLetter


class RoleMatchAnalysis(Base):
    __tablename__ = "role_match_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_analysis_id = Column(Integer, ForeignKey("role_match_analysis.id", ondelete="SET NULL"), nullable=True)
    superseded_by_id = Column(Integer, ForeignKey("role_match_analysis.id", ondelete="SET NULL"), nullable=True)
    profile_id = Column(Integer, ForeignKey("profile.id", ondelete="SET NULL"), nullable=True)
    application_id = Column(Integer, ForeignKey("application.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    analysis_date = Column(Date, nullable=False)
    state = Column(String(32), nullable=False)
    job_description = Column(Text, nullable=False)
    job_description_hash = Column(String(64), nullable=False, index=True)
    safe_profile_snapshot = Column(Text, nullable=False)
    safe_profile_hash = Column(String(64), nullable=False, index=True)
    rules_version = Column(String(64), nullable=False)
    prompt_version = Column(String(64), nullable=False)
    model_provider = Column(String(255), nullable=True)
    model_name = Column(String(255), nullable=True)
    raw_llm_output = Column(Text, nullable=True)
    normalized_payload = Column(Text, nullable=True)
    scoring_payload = Column(Text, nullable=True)
    raw_score = Column(Float, nullable=True)
    display_score = Column(Integer, nullable=True)
    score_band = Column(String(64), nullable=True)
    confidence_score = Column(Float, nullable=True)
    confidence_band = Column(String(32), nullable=True)
    eligibility_status = Column(String(32), nullable=False)
    show_authoritative_score = Column(Boolean, nullable=False, default=False)
    failure_code = Column(String(64), nullable=True)
    excluded_items = Column(Text, nullable=False, default="[]")


# This column belongs to the legacy cover-letter table but is declared here so
# importing the role-match subsystem is enough to register the complete v1.3
# ORM metadata without coupling the legacy models module to the new engine.
GeneratedCoverLetter.role_match_analysis_id = Column(
    Integer,
    ForeignKey("role_match_analysis.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)


class RoleMatchRequirement(Base):
    __tablename__ = "role_match_requirement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("role_match_analysis.id", ondelete="CASCADE"), nullable=False, index=True)
    cluster_id = Column(String(255), nullable=False)
    canonical_key = Column(String(255), nullable=False)
    canonical_text = Column(Text, nullable=False)
    primary_category = Column(String(64), nullable=False)
    extracted_importance = Column(String(32), nullable=False)
    effective_importance = Column(String(32), nullable=False)
    mention_count = Column(Integer, nullable=False)
    importance_conflict = Column(Boolean, nullable=False, default=False)
    importance_mentions = Column(Text, nullable=False)
    source_quotes = Column(Text, nullable=False)
    volatility = Column(String(32), nullable=False)
    minimum_months = Column(Integer, nullable=True)
    tool_specificity = Column(String(32), nullable=False)
    excluded = Column(Boolean, nullable=False, default=False)
    exclusion_reason = Column(Text, nullable=True)
    match_level = Column(String(32), nullable=True)
    strength = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)


class RoleMatchEvidence(Base):
    __tablename__ = "role_match_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("role_match_analysis.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("role_match_requirement.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(String(255), nullable=False)
    source_type = Column(String(64), nullable=False)
    source_text = Column(Text, nullable=False)
    relationship = Column(String(64), nullable=False)
    depth = Column(String(64), nullable=False)
    recency_multiplier = Column(Float, nullable=False)
    base_strength = Column(Float, nullable=False)
    duplicate = Column(Boolean, nullable=False, default=False)
    contradiction = Column(Boolean, nullable=False, default=False)
    explanation = Column(Text, nullable=True)
    rank = Column(Integer, nullable=False, default=0)


class RoleMatchOverride(Base):
    __tablename__ = "role_match_override"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("role_match_analysis.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_key = Column(String(255), nullable=False)
    field_name = Column(String(64), nullable=False)
    extracted_value = Column(Text, nullable=True)
    effective_value = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    source = Column(String(32), nullable=False, default="user")
    carry_status = Column(String(32), nullable=False, default="carried_forward")
    source_override_id = Column(Integer, ForeignKey("role_match_override.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
