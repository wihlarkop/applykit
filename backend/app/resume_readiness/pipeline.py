from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.resume_readiness.coverage import calculate_source_coverage
from app.resume_readiness.domain import (
    AnalysisMode,
    AnalysisStatus,
    Category,
    ExtractedDocument,
    OverallResult,
    ReadinessResult,
    RuleOutcome,
    RuleResult,
)
from app.resume_readiness.extraction import extract_pdf
from app.resume_readiness.rules_parseability import evaluate_parseability
from app.resume_readiness.rules_quality import evaluate_quality
from app.resume_readiness.rules_tailoring import evaluate_tailoring
from app.resume_readiness.scoring import (
    calculate_category_score,
    calculate_overall_result,
)
from integration.pdf import html_to_pdf
from integration.template import render_cv_template


@dataclass(frozen=True)
class AnalysisInput:
    generated_cv_id: int
    profile_snapshot: dict[str, Any]
    job_description: str | None = None
    role_match: Any | None = None


@dataclass(frozen=True)
class PipelineDependencies:
    render_pdf: Callable[[dict[str, Any]], bytes]
    extract_pdf: Callable[[bytes], ExtractedDocument]


def _render_profile_pdf(snapshot: dict[str, Any]) -> bytes:
    return html_to_pdf(render_cv_template(snapshot))


DEFAULT_DEPENDENCIES = PipelineDependencies(
    render_pdf=_render_profile_pdf,
    extract_pdf=extract_pdf,
)


def _failure(mode: AnalysisMode, code: str) -> ReadinessResult:
    overall = OverallResult.failed(code)
    return ReadinessResult(
        mode=mode,
        status=AnalysisStatus.FAILED,
        overall=overall,
        parseability=None,
        quality=None,
        tailoring=None,
        rule_results=(),
        extraction=None,
        coverage=None,
        failure_code=code,
    )


def _hard_gate(rules: list[RuleResult]) -> tuple[str | None, int | None]:
    capped = [rule for rule in rules if rule.score_cap is not None]
    if not capped:
        return None, None
    winner = min(capped, key=lambda rule: int(rule.score_cap or 100))
    return winner.rule_id, winner.score_cap


def _requires_human_review(rules: list[RuleResult]) -> bool:
    definitive_no_text = any(
        rule.rule_id == "PARSE-001" and rule.outcome == RuleOutcome.FAIL
        for rule in rules
    )
    if definitive_no_text:
        return False
    return any(rule.requires_review for rule in rules)


def analyze_generated_cv(
    analysis_input: AnalysisInput,
    dependencies: PipelineDependencies = DEFAULT_DEPENDENCIES,
) -> ReadinessResult:
    mode = (
        AnalysisMode.JOB_SPECIFIC
        if analysis_input.job_description and analysis_input.job_description.strip()
        else AnalysisMode.GENERAL
    )

    try:
        pdf_bytes = dependencies.render_pdf(analysis_input.profile_snapshot)
    except Exception:
        return _failure(mode, "PDF_RENDER_FAILED")

    try:
        extracted = dependencies.extract_pdf(pdf_bytes)
    except Exception:
        return _failure(mode, "PDF_PARSE_FAILED")

    coverage = calculate_source_coverage(
        analysis_input.profile_snapshot,
        extracted.text,
    )
    parseability_rules = evaluate_parseability(
        analysis_input.profile_snapshot,
        extracted,
        coverage,
    )
    quality_rules = evaluate_quality(
        analysis_input.profile_snapshot,
        extracted,
    )
    tailoring_rules = (
        evaluate_tailoring(
            analysis_input.profile_snapshot,
            analysis_input.job_description,
            analysis_input.role_match,
        )
        if mode == AnalysisMode.JOB_SPECIFIC
        else []
    )
    all_rules = [*parseability_rules, *quality_rules, *tailoring_rules]

    parseability = calculate_category_score(Category.PARSEABILITY, all_rules)
    quality = calculate_category_score(Category.QUALITY, all_rules)
    tailoring = (
        calculate_category_score(Category.TAILORING, all_rules)
        if mode == AnalysisMode.JOB_SPECIFIC
        else None
    )
    hard_gate, hard_gate_cap = _hard_gate(all_rules)
    overall = calculate_overall_result(
        mode=mode,
        parseability_score=parseability.score,
        quality_score=quality.score,
        tailoring_score=tailoring.score if tailoring else None,
        hard_gate=hard_gate,
        hard_gate_cap=hard_gate_cap,
        needs_review=_requires_human_review(all_rules),
    )

    return ReadinessResult(
        mode=mode,
        status=overall.status,
        overall=overall,
        parseability=parseability,
        quality=quality,
        tailoring=tailoring,
        rule_results=tuple(all_rules),
        extraction=extracted,
        coverage=coverage,
    )
