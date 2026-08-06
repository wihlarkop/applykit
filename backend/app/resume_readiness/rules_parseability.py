from __future__ import annotations

from typing import Any

from app.resume_readiness.constants import (
    MINIMUM_USABLE_TEXT_CHARS,
    SOURCE_COVERAGE_REVIEW_THRESHOLD,
    SOURCE_COVERAGE_WARNING_THRESHOLD,
)
from app.resume_readiness.domain import (
    Category,
    CoverageResult,
    ExtractedDocument,
    RuleResult,
    Severity,
)
from app.resume_readiness.normalization import normalize_text


def _contains(extracted_text: str, value: str | None) -> bool:
    normalized = normalize_text(value)
    return bool(normalized and normalized in normalize_text(extracted_text))


def _missing_prefix(coverage: CoverageResult, prefix: str) -> bool:
    return any(item.key.startswith(prefix) for item in coverage.missing)


def evaluate_parseability(
    snapshot: dict[str, Any],
    extracted: ExtractedDocument,
    coverage: CoverageResult,
) -> list[RuleResult]:
    results: list[RuleResult] = []

    if not extracted.has_text_layer:
        results.append(
            RuleResult.fail(
                rule_id="PARSE-001",
                category=Category.PARSEABILITY,
                score_delta=-80,
                score_cap=20,
                title="No usable text layer",
                explanation="The generated PDF does not expose selectable text for parsing.",
                evidence={"page_count": extracted.page_count},
            )
        )
    else:
        results.append(
            RuleResult.passed(
                rule_id="PARSE-001",
                category=Category.PARSEABILITY,
                title="Usable text layer detected",
                explanation="The generated PDF exposes selectable text.",
            )
        )

    if 0 < len(extracted.text.strip()) < MINIMUM_USABLE_TEXT_CHARS:
        results.append(
            RuleResult.fail(
                rule_id="PARSE-002",
                category=Category.PARSEABILITY,
                score_delta=-30,
                score_cap=55,
                title="Extracted text is unexpectedly short",
                explanation="The PDF text is too short to represent the source resume reliably.",
                evidence={"character_count": len(extracted.text.strip())},
                requires_review=True,
            )
        )

    if snapshot.get("name") and not _contains(extracted.text, snapshot.get("name")):
        results.append(
            RuleResult.fail(
                rule_id="PARSE-003",
                category=Category.PARSEABILITY,
                score_delta=-10,
                title="Name was not extracted",
                explanation="The source profile contains a name that is missing from extracted PDF text.",
                evidence={"source_value": snapshot.get("name")},
                severity=Severity.IMPORTANT,
            )
        )

    if snapshot.get("email") and not _contains(extracted.text, snapshot.get("email")):
        results.append(
            RuleResult.fail(
                rule_id="PARSE-004",
                category=Category.PARSEABILITY,
                score_delta=-20,
                score_cap=60,
                title="Email was not extracted",
                explanation="The source profile email is missing from extracted PDF text.",
                evidence={"source_value": snapshot.get("email")},
            )
        )

    phone = snapshot.get("phone")
    if not phone:
        results.append(
            RuleResult.excluded(
                rule_id="PARSE-005",
                category=Category.PARSEABILITY,
                title="Phone check not applicable",
                explanation="The source profile does not contain a phone number.",
            )
        )
    elif not _contains(extracted.text, phone):
        results.append(
            RuleResult.fail(
                rule_id="PARSE-006",
                category=Category.PARSEABILITY,
                score_delta=-8,
                title="Phone number was not extracted",
                explanation="The source profile phone number is missing from extracted PDF text.",
                evidence={"source_value": phone},
                severity=Severity.IMPORTANT,
            )
        )

    experiences = snapshot.get("work_experience") or []
    if experiences and any(
        key.startswith("experience:")
        and (key.endswith(":role") or key.endswith(":company"))
        for key in coverage.missing_critical
    ):
        results.append(
            RuleResult.fail(
                rule_id="PARSE-007",
                category=Category.PARSEABILITY,
                score_delta=-25,
                score_cap=55,
                title="Experience structure was not extracted reliably",
                explanation="At least one source role or company is missing from extracted PDF text.",
                evidence={"missing": list(coverage.missing_critical)},
                requires_review=True,
            )
        )

    if snapshot.get("education") and _missing_prefix(coverage, "education:"):
        results.append(
            RuleResult.fail(
                rule_id="PARSE-008",
                category=Category.PARSEABILITY,
                score_delta=-8,
                title="Education content is partially missing",
                explanation="At least one education field from the source was not extracted.",
                evidence={
                    "missing": [
                        item.key
                        for item in coverage.missing
                        if item.key.startswith("education:")
                    ]
                },
                severity=Severity.IMPORTANT,
            )
        )

    if snapshot.get("skills") and _missing_prefix(coverage, "skill:"):
        missing_skills = [
            item.key for item in coverage.missing if item.key.startswith("skill:")
        ]
        results.append(
            RuleResult.warning(
                rule_id="PARSE-009",
                category=Category.PARSEABILITY,
                score_delta=max(-8, -2 * len(missing_skills)),
                title="Some skills were not extracted",
                explanation="One or more source skills are absent from extracted PDF text.",
                evidence={"missing": missing_skills},
                severity=Severity.IMPORTANT,
            )
        )

    if "reading_order_risk" in extracted.warnings:
        results.append(
            RuleResult.warning(
                rule_id="PARSE-010",
                category=Category.PARSEABILITY,
                score_delta=-10,
                title="Reading order may be inconsistent",
                explanation="The extracted sequence suggests a possible multi-column ordering issue.",
                evidence={"warnings": list(extracted.warnings)},
                severity=Severity.IMPORTANT,
            )
        )

    repeated = [warning for warning in extracted.warnings if "repeated_" in warning]
    if repeated:
        results.append(
            RuleResult.warning(
                rule_id="PARSE-011",
                category=Category.PARSEABILITY,
                score_delta=-4,
                title="Repeated header or footer text detected",
                explanation="Repeated page furniture may pollute machine extraction.",
                evidence={"warnings": repeated},
            )
        )

    if coverage.coverage < SOURCE_COVERAGE_REVIEW_THRESHOLD:
        results.append(
            RuleResult.fail(
                rule_id="PARSE-012",
                category=Category.PARSEABILITY,
                score_delta=-25,
                score_cap=55,
                title="Source-to-PDF coverage is too low",
                explanation="Too much source profile evidence is missing from extracted PDF text.",
                evidence={"coverage": coverage.coverage},
                requires_review=True,
            )
        )
    elif coverage.coverage < SOURCE_COVERAGE_WARNING_THRESHOLD:
        results.append(
            RuleResult.warning(
                rule_id="PARSE-013",
                category=Category.PARSEABILITY,
                score_delta=-10,
                title="Source-to-PDF coverage is partial",
                explanation="Some source profile evidence is missing from extracted PDF text.",
                evidence={"coverage": coverage.coverage},
                severity=Severity.IMPORTANT,
            )
        )
    else:
        results.append(
            RuleResult.passed(
                rule_id="PARSE-013",
                category=Category.PARSEABILITY,
                title="Source-to-PDF coverage is strong",
                explanation="Most weighted source profile evidence is present in extracted PDF text.",
                evidence={"coverage": coverage.coverage},
            )
        )

    missing_dates: list[str] = []
    for index, experience in enumerate(experiences):
        for field in ("start_date", "end_date"):
            value = experience.get(field)
            if value and not _contains(extracted.text, value):
                missing_dates.append(f"experience:{index}:{field}")
    if missing_dates:
        results.append(
            RuleResult.warning(
                rule_id="PARSE-014",
                category=Category.PARSEABILITY,
                score_delta=max(-8, -2 * len(missing_dates)),
                title="Some experience dates were not extracted",
                explanation="Dates from the source profile could not be found in extracted PDF text.",
                evidence={"missing": missing_dates},
                severity=Severity.IMPORTANT,
            )
        )

    return results
