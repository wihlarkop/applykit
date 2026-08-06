from __future__ import annotations

from app.resume_readiness.domain import AnalysisMode, Category

RULES_VERSION = "resume-readiness-v1"
EXTRACTION_VERSION = "resume-readiness-extraction-v1"
SEMANTIC_VERSION = "resume-readiness-semantic-v1"

PDF_MAX_BYTES = 5 * 1024 * 1024
PDF_MAX_PAGES = 10
EXTRACTED_TEXT_MAX_CHARS = 100_000
DEFAULT_FINDING_LIMIT = 100

GENERAL_WEIGHTS = {
    Category.PARSEABILITY: 0.55,
    Category.QUALITY: 0.45,
}

JOB_SPECIFIC_WEIGHTS = {
    Category.PARSEABILITY: 0.40,
    Category.QUALITY: 0.35,
    Category.TAILORING: 0.25,
}

WEIGHTS_BY_MODE = {
    AnalysisMode.GENERAL: GENERAL_WEIGHTS,
    AnalysisMode.JOB_SPECIFIC: JOB_SPECIFIC_WEIGHTS,
}

BANDS = (
    (90, "excellent"),
    (75, "good"),
    (60, "needs_improvement"),
    (0, "not_ready"),
)

MINIMUM_USABLE_TEXT_CHARS = 80
SOURCE_COVERAGE_REVIEW_THRESHOLD = 0.70
SOURCE_COVERAGE_WARNING_THRESHOLD = 0.85
SUMMARY_MAX_WORDS = 120
BULLET_MAX_WORDS = 45
BULLET_MIN_WORDS = 4
MAX_REPEATED_RULE_DEDUCTION = -20
KEYWORD_REPETITION_THRESHOLD = 5
