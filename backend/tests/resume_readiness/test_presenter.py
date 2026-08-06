from datetime import UTC, datetime
from types import SimpleNamespace

from app.resume_readiness.presenter import present_analysis


def _analysis(*, status="complete", score=60, band="needs_improvement"):
    rule = SimpleNamespace(
        id=1,
        rule_id="PARSE-004",
        category="parseability",
        severity="critical",
        outcome="fail",
        score_delta=-20,
        score_cap=60,
        title="Email was not extracted",
        explanation="The source email is missing from extracted text.",
        evidence_json='{"source_value":"edo@example.com"}',
        locations_json="[]",
        requires_review=False,
    )
    return SimpleNamespace(
        id=10,
        generated_cv_id=5,
        profile_id=2,
        role_match_analysis_id=None,
        supersedes_analysis_id=None,
        mode="general",
        status=status,
        overall_score=score,
        overall_band=band,
        parseability_score=60 if score is not None else None,
        parseability_band="needs_improvement" if score is not None else None,
        quality_score=80 if score is not None else None,
        quality_band="good" if score is not None else None,
        tailoring_score=None,
        tailoring_band=None,
        hard_gate_code="PARSE-004" if score is not None else None,
        failure_code="PDF_PARSE_FAILED" if status == "failed" else None,
        extraction_json=None,
        rules_version="resume-readiness-v1",
        extraction_version="resume-readiness-extraction-v1",
        semantic_version=None,
        created_at=datetime.now(UTC),
        rule_results=[rule] if score is not None else [],
    )


def test_presenter_derives_category_score_cap_from_findings():
    response = present_analysis(_analysis())

    assert response.categories.parseability is not None
    assert response.categories.parseability.score_cap == 60
    assert response.overall.hard_gate == "PARSE-004"


def test_presenter_keeps_failed_analysis_unscored():
    response = present_analysis(_analysis(status="failed", score=None, band=None))

    assert response.status == "failed"
    assert response.overall.score is None
    assert response.overall.band is None
    assert response.failure_code == "PDF_PARSE_FAILED"
