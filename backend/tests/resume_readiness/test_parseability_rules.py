from app.resume_readiness.domain import (
    CoverageResult,
    EvidencePhrase,
    ExtractedDocument,
    RuleOutcome,
)
from app.resume_readiness.rules_parseability import evaluate_parseability


def _coverage(value: float, missing: tuple[EvidencePhrase, ...] = ()) -> CoverageResult:
    return CoverageResult(coverage=value, matched=(), missing=missing)


def test_image_only_pdf_triggers_parse_001():
    results = evaluate_parseability(
        snapshot={"name": "Edo", "email": "edo@example.com", "work_experience": []},
        extracted=ExtractedDocument(
            text="",
            pages=(),
            page_count=1,
            has_text_layer=False,
            warnings=("page_1_has_no_text",),
        ),
        coverage=_coverage(0.0),
    )

    rule = next(result for result in results if result.rule_id == "PARSE-001")
    assert rule.outcome == RuleOutcome.FAIL
    assert rule.score_cap == 20


def test_missing_source_experience_triggers_review_cap():
    missing = (
        EvidencePhrase(
            key="experience:0:role",
            value="Engineer",
            weight=3,
            critical=True,
        ),
    )
    results = evaluate_parseability(
        snapshot={
            "name": "Edo",
            "email": "edo@example.com",
            "work_experience": [
                {"company": "Example", "role": "Engineer", "bullets": []}
            ],
        },
        extracted=ExtractedDocument(
            text="Edo edo@example.com Example",
            pages=(),
            page_count=1,
            has_text_layer=True,
        ),
        coverage=_coverage(0.5, missing),
    )

    rule = next(result for result in results if result.rule_id == "PARSE-007")
    assert rule.score_cap == 55
    assert rule.requires_review is True


def test_strong_coverage_records_a_pass():
    results = evaluate_parseability(
        snapshot={"name": "Edo", "email": "edo@example.com", "work_experience": []},
        extracted=ExtractedDocument(
            text="Edo edo@example.com Backend Engineer with Python experience",
            pages=(),
            page_count=1,
            has_text_layer=True,
        ),
        coverage=_coverage(0.95),
    )

    rule = next(result for result in results if result.rule_id == "PARSE-013")
    assert rule.outcome == RuleOutcome.PASS
