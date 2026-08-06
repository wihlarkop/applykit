from dataclasses import dataclass

from app.role_match.domain import (
    EvidenceDepth,
    EvidenceRelationship,
    EvidenceSource,
    RequirementCategory,
    RequirementImportance,
)

RULES_VERSION = "role-match-v1"
PROMPT_VERSION = "role-match-extraction-v1"

CATEGORY_WEIGHTS = {
    RequirementCategory.ESSENTIAL_QUALIFICATIONS: 0.30,
    RequirementCategory.RELEVANT_COMPETENCIES: 0.30,
    RequirementCategory.RELEVANT_WORK_TASKS: 0.25,
    RequirementCategory.PREFERRED_QUALIFICATIONS: 0.10,
    RequirementCategory.CONTEXTUAL_ALIGNMENT: 0.05,
}

IMPORTANCE_WEIGHTS = {
    RequirementImportance.CRITICAL: 1.00,
    RequirementImportance.IMPORTANT: 0.70,
    RequirementImportance.SUPPORTING: 0.40,
}

SOURCE_MULTIPLIERS = {
    EvidenceSource.WORK_EXPERIENCE: 1.00,
    EvidenceSource.PROJECT: 0.80,
    EvidenceSource.CERTIFICATION_EDUCATION: 0.60,
    EvidenceSource.SKILLS_LIST: 0.35,
}

DEPTH_MULTIPLIERS = {
    EvidenceDepth.PRODUCTION_OWNERSHIP: 1.00,
    EvidenceDepth.HANDS_ON_CONTRIBUTION: 0.80,
    EvidenceDepth.EXPOSURE_ONLY: 0.45,
}

RELATIONSHIP_MULTIPLIERS = {
    EvidenceRelationship.EXACT: 1.00,
    EvidenceRelationship.FUNCTIONAL_EQUIVALENT: 0.75,
    EvidenceRelationship.ADJACENT: 0.40,
    EvidenceRelationship.UNRELATED: 0.00,
}

CONFIDENCE_WEIGHTS = {
    "known_coverage": 0.45,
    "evidence_reliability": 0.35,
    "evidence_consistency": 0.20,
}

UNSUPPORTED_ESSENTIAL_CAPS = {1: 74, 2: 59, 3: 44}
UNKNOWN_ESSENTIAL_CAPS = {1: 89, 2: 79, 3: 69}

AUTOMATIC_CLUSTER_SIMILARITY = 0.88
CLUSTER_REVIEW_SIMILARITY = 0.72
AUTOMATIC_OVERRIDE_CARRY_SIMILARITY = 0.92
OVERRIDE_REVIEW_SIMILARITY = 0.75
EXTRACTION_ATTEMPTS = 2


@dataclass(frozen=True)
class DisplayRules:
    minimum_known_coverage: float = 0.60
    minimum_confidence: float = 0.55
    maximum_unresolved_conflict_rate: float = 0.20
    minimum_atomic_requirements: int = 3


DISPLAY_RULES = DisplayRules()
