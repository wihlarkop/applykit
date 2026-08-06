from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RequirementCategory(str, Enum):
    ESSENTIAL_QUALIFICATIONS = "essential_qualifications"
    RELEVANT_COMPETENCIES = "relevant_competencies"
    RELEVANT_WORK_TASKS = "relevant_work_tasks"
    PREFERRED_QUALIFICATIONS = "preferred_qualifications"
    CONTEXTUAL_ALIGNMENT = "contextual_alignment"
    ELIGIBILITY = "eligibility"
    TRAINABLE = "trainable"


class RequirementImportance(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    SUPPORTING = "supporting"


class EvidenceSource(str, Enum):
    WORK_EXPERIENCE = "work_experience"
    PROJECT = "project"
    CERTIFICATION_EDUCATION = "certification_education"
    SKILLS_LIST = "skills_list"


class EvidenceDepth(str, Enum):
    PRODUCTION_OWNERSHIP = "production_ownership"
    HANDS_ON_CONTRIBUTION = "hands_on_contribution"
    EXPOSURE_ONLY = "exposure_only"


class EvidenceRelationship(str, Enum):
    EXACT = "exact"
    FUNCTIONAL_EQUIVALENT = "functional_equivalent"
    ADJACENT = "adjacent"
    UNRELATED = "unrelated"


class TechnologyVolatility(str, Enum):
    STABLE = "stable"
    EVOLVING = "evolving"
    FAST_MOVING = "fast_moving"


class MatchLevel(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NO_EVIDENCE = "no_evidence"
    UNKNOWN = "unknown"
    CONTRADICTORY = "contradictory_evidence"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    LIKELY_ELIGIBLE = "likely_eligible"
    UNCLEAR = "eligibility_unclear"
    LIKELY_INELIGIBLE = "likely_ineligible"
    INELIGIBLE = "ineligible"


class ConfidenceBand(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnalysisState(str, Enum):
    SUCCESS = "success"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    EXTRACTED = "extracted"


class OverrideCarryStatus(str, Enum):
    CARRIED_FORWARD = "carried_forward"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


ToolSpecificity = Literal["capability", "example_set", "specific", "operational"]


class AtomicRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    text: str
    canonical_key: str
    primary_category: RequirementCategory
    importance: RequirementImportance
    source_quote: str
    is_eligibility: bool = False
    is_trainable: bool = False
    volatility: TechnologyVolatility = TechnologyVolatility.EVOLVING
    minimum_months: int | None = Field(default=None, ge=0)
    tool_specificity: ToolSpecificity = "capability"
    excluded: bool = False
    exclusion_reason: str | None = None


class RequirementCluster(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: str
    canonical_requirement: str
    canonical_key: str
    primary_category: RequirementCategory
    importance: RequirementImportance
    mention_count: int = Field(ge=1)
    importance_conflict: bool
    importance_mentions: dict[RequirementImportance, int]
    source_quotes: list[str]
    source_ids: list[str]
    is_eligibility: bool
    is_trainable: bool
    volatility: TechnologyVolatility
    minimum_months: int | None = Field(default=None, ge=0)
    tool_specificity: ToolSpecificity
    excluded: bool = False
    exclusion_reason: str | None = None


class ClusteringConflict(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical_key: str
    source_ids: list[str]
    reason: str


class ClusteringReviewCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    left_key: str
    right_key: str
    similarity: float


class ClusteringResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    clusters: list[RequirementCluster]
    review_candidates: list[ClusteringReviewCandidate] = []
    unresolved_conflicts: list[ClusteringConflict] = []


class SafeWorkExperience(BaseModel):
    model_config = ConfigDict(frozen=True)

    company: str
    role: str
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = []


class SafeEducation(BaseModel):
    model_config = ConfigDict(frozen=True)

    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class SafeProject(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None
    tech_stack: list[str] = []


class SafeCertification(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = None
    issuer: str | None = None
    date: str | None = None


class SafeProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    location: str | None = None
    summary: str | None = None
    work_experience: list[SafeWorkExperience] = []
    education: list[SafeEducation] = []
    skills: list[str] = []
    projects: list[SafeProject] = []
    certifications: list[SafeCertification] = []


class EvidenceCatalogItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    source: EvidenceSource
    text: str
    start_date: str | None = None
    end_date: str | None = None
    metadata: dict[str, Any] = {}
    duplicate_key: str | None = None


class EvidenceLink(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_id: str
    evidence_id: str
    source: EvidenceSource
    relationship: EvidenceRelationship
    depth: EvidenceDepth
    volatility: TechnologyVolatility = TechnologyVolatility.EVOLVING
    last_used_date: date | None = None
    is_current: bool = False
    is_duplicate: bool = False
    is_contradiction: bool = False
    explanation: str = ""
    precomputed_strength: float | None = Field(default=None, ge=0.0, le=1.0)


class RequirementAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: str
    category: RequirementCategory
    importance: RequirementImportance
    match_level: MatchLevel
    strength: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_links: list[EvidenceLink] = []
    explanation: str = ""
    known: bool = True
    confidence_evidence_count: int = 0


class CategoryAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: RequirementCategory
    score: float = Field(ge=0.0, le=1.0)
    known_coverage: float = Field(ge=0.0, le=1.0)
    unknown_coverage: float = Field(ge=0.0, le=1.0)
    known_match: float = Field(ge=0.0, le=1.0)
    requirement_count: int = Field(ge=0)


class ScoreResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    category_assessments: list[CategoryAssessment]
    raw_score: float = Field(ge=0.0, le=100.0)
    capped_score: float = Field(ge=0.0, le=100.0)
    display_score: int = Field(ge=0, le=100)
    score_band: str
    applied_cap: int | None = None
    unsupported_essential_count: int = 0
    unknown_essential_count: int = 0


class ConfidenceInputs(BaseModel):
    model_config = ConfigDict(frozen=True)

    known_coverage: float = Field(ge=0.0, le=1.0)
    evidence_reliability: float = Field(ge=0.0, le=1.0)
    evidence_consistency: float = Field(ge=0.0, le=1.0)


class ConfidenceAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=1.0)
    band: ConfidenceBand
    explanation: str


class EligibilitySignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_id: str
    mandatory: bool = True
    explicit_support: bool = False
    explicit_contradiction: bool = False
    likely_contradiction: bool = False
    unknown: bool = True
    reason: str = ""


class EligibilityAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: EligibilityStatus
    reasons: list[str] = []


class DisplayDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    show_score: bool
    reason: str | None = None


class FairnessDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    excluded: bool
    action: Literal["include", "review", "exclude_warn_continue"]
    reason: str


class AnalysisInsight(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    explanation: str
    evidence_label: str | None = None


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    headline: str
    description: str
    strengths: list[AnalysisInsight] = []
    concerns: list[AnalysisInsight] = []
    next_step: str
