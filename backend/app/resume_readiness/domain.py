from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AnalysisMode(StrEnum):
    GENERAL = "general"
    JOB_SPECIFIC = "job_specific"


class AnalysisStatus(StrEnum):
    COMPLETE = "complete"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class Category(StrEnum):
    PARSEABILITY = "parseability"
    QUALITY = "quality"
    TAILORING = "tailoring"


class RuleOutcome(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    UNKNOWN = "unknown"
    EXCLUDED = "excluded"


class Severity(StrEnum):
    INFO = "info"
    IMPROVEMENT = "improvement"
    IMPORTANT = "important"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    category: Category
    severity: Severity
    outcome: RuleOutcome
    title: str
    explanation: str
    score_delta: int = 0
    score_cap: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    locations: tuple[str, ...] = ()
    requires_review: bool = False

    @classmethod
    def passed(
        cls,
        *,
        rule_id: str,
        category: Category,
        title: str,
        explanation: str,
        evidence: dict[str, Any] | None = None,
        locations: tuple[str, ...] = (),
    ) -> "RuleResult":
        return cls(
            rule_id=rule_id,
            category=category,
            severity=Severity.INFO,
            outcome=RuleOutcome.PASS,
            title=title,
            explanation=explanation,
            evidence=evidence or {},
            locations=locations,
        )

    @classmethod
    def warning(
        cls,
        *,
        rule_id: str,
        category: Category,
        title: str,
        explanation: str,
        score_delta: int = 0,
        score_cap: int | None = None,
        evidence: dict[str, Any] | None = None,
        locations: tuple[str, ...] = (),
        severity: Severity = Severity.IMPROVEMENT,
        requires_review: bool = False,
    ) -> "RuleResult":
        return cls(
            rule_id=rule_id,
            category=category,
            severity=severity,
            outcome=RuleOutcome.WARNING,
            score_delta=score_delta,
            score_cap=score_cap,
            title=title,
            explanation=explanation,
            evidence=evidence or {},
            locations=locations,
            requires_review=requires_review,
        )

    @classmethod
    def fail(
        cls,
        *,
        rule_id: str,
        category: Category,
        title: str,
        explanation: str,
        score_delta: int = 0,
        score_cap: int | None = None,
        evidence: dict[str, Any] | None = None,
        locations: tuple[str, ...] = (),
        severity: Severity = Severity.CRITICAL,
        requires_review: bool = False,
    ) -> "RuleResult":
        return cls(
            rule_id=rule_id,
            category=category,
            severity=severity,
            outcome=RuleOutcome.FAIL,
            score_delta=score_delta,
            score_cap=score_cap,
            title=title,
            explanation=explanation,
            evidence=evidence or {},
            locations=locations,
            requires_review=requires_review,
        )

    @classmethod
    def unknown(
        cls,
        *,
        rule_id: str,
        category: Category,
        title: str,
        explanation: str,
        evidence: dict[str, Any] | None = None,
        locations: tuple[str, ...] = (),
    ) -> "RuleResult":
        return cls(
            rule_id=rule_id,
            category=category,
            severity=Severity.INFO,
            outcome=RuleOutcome.UNKNOWN,
            title=title,
            explanation=explanation,
            evidence=evidence or {},
            locations=locations,
        )

    @classmethod
    def excluded(
        cls,
        *,
        rule_id: str,
        category: Category,
        title: str,
        explanation: str,
        evidence: dict[str, Any] | None = None,
    ) -> "RuleResult":
        return cls(
            rule_id=rule_id,
            category=category,
            severity=Severity.INFO,
            outcome=RuleOutcome.EXCLUDED,
            title=title,
            explanation=explanation,
            evidence=evidence or {},
        )


@dataclass(frozen=True)
class CategoryResult:
    category: Category
    raw_score: int
    score: int
    band: str
    score_cap: int | None


@dataclass(frozen=True)
class OverallResult:
    status: AnalysisStatus
    score: int | None
    band: str | None
    hard_gate: str | None = None
    failure_code: str | None = None

    @classmethod
    def failed(cls, failure_code: str) -> "OverallResult":
        return cls(
            status=AnalysisStatus.FAILED,
            score=None,
            band=None,
            failure_code=failure_code,
        )


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    pages: tuple[ExtractedPage, ...]
    page_count: int
    has_text_layer: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidencePhrase:
    key: str
    value: str
    weight: float
    critical: bool = False
    location: str | None = None


@dataclass(frozen=True)
class CoverageResult:
    coverage: float
    matched: tuple[EvidencePhrase, ...]
    missing: tuple[EvidencePhrase, ...]

    @property
    def missing_critical(self) -> tuple[str, ...]:
        return tuple(item.key for item in self.missing if item.critical)


@dataclass(frozen=True)
class ReadinessResult:
    mode: AnalysisMode
    status: AnalysisStatus
    overall: OverallResult
    parseability: CategoryResult | None
    quality: CategoryResult | None
    tailoring: CategoryResult | None
    rule_results: tuple[RuleResult, ...]
    extraction: ExtractedDocument | None = None
    coverage: CoverageResult | None = None
    failure_code: str | None = None
