from __future__ import annotations

from collections.abc import Iterable

from app.resume_readiness.constants import BANDS, WEIGHTS_BY_MODE
from app.resume_readiness.domain import (
    AnalysisMode,
    AnalysisStatus,
    Category,
    CategoryResult,
    OverallResult,
    RuleResult,
)


def band_for_score(score: int) -> str:
    for minimum, band in BANDS:
        if score >= minimum:
            return band
    return "not_ready"


def calculate_category_score(
    category: Category,
    rules: Iterable[RuleResult],
) -> CategoryResult:
    matching = [rule for rule in rules if rule.category == category]
    raw_score = max(0, min(100, 100 + sum(rule.score_delta for rule in matching)))
    caps = [rule.score_cap for rule in matching if rule.score_cap is not None]
    score_cap = min(caps) if caps else None
    score = min(raw_score, score_cap) if score_cap is not None else raw_score
    return CategoryResult(
        category=category,
        raw_score=raw_score,
        score=score,
        band=band_for_score(score),
        score_cap=score_cap,
    )


def calculate_overall_result(
    *,
    mode: AnalysisMode,
    parseability_score: int,
    quality_score: int,
    tailoring_score: int | None,
    hard_gate: str | None,
    hard_gate_cap: int | None = None,
    needs_review: bool = False,
) -> OverallResult:
    weights = WEIGHTS_BY_MODE[mode]
    category_scores: dict[Category, int] = {
        Category.PARSEABILITY: parseability_score,
        Category.QUALITY: quality_score,
    }
    if mode == AnalysisMode.JOB_SPECIFIC:
        if tailoring_score is None:
            raise ValueError("tailoring_score is required for job-specific analysis")
        category_scores[Category.TAILORING] = tailoring_score

    weighted_score = round(
        sum(category_scores[category] * weight for category, weight in weights.items())
    )
    final_score = (
        min(weighted_score, hard_gate_cap)
        if hard_gate_cap is not None
        else weighted_score
    )
    return OverallResult(
        status=(
            AnalysisStatus.NEEDS_REVIEW if needs_review else AnalysisStatus.COMPLETE
        ),
        score=final_score,
        band=band_for_score(final_score),
        hard_gate=hard_gate,
    )
