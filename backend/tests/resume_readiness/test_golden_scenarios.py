import pytest

from app.resume_readiness.domain import ExtractedDocument
from app.resume_readiness.pipeline import (
    AnalysisInput,
    PipelineDependencies,
    analyze_generated_cv,
)


PROFILE = {
    "name": "Edo Example",
    "email": "edo@example.com",
    "phone": "+62 812 0000 0000",
    "summary": "Backend engineer building reliable API and event-driven systems.",
    "work_experience": [
        {
            "company": "Example Corp",
            "role": "Backend Engineer",
            "start_date": "2022-01",
            "end_date": "Present",
            "bullets": [
                "Built Python APIs and improved request latency by 20%",
            ],
        }
    ],
    "education": [],
    "skills": ["Python", "FastAPI"],
}

FULL_TEXT = (
    "Edo Example edo@example.com +62 812 0000 0000 "
    "Backend engineer building reliable API and event-driven systems. "
    "Backend Engineer Example Corp 2022-01 Present "
    "Built Python APIs and improved request latency by 20% Python FastAPI"
)


def dependencies(document: ExtractedDocument) -> PipelineDependencies:
    return PipelineDependencies(
        render_pdf=lambda snapshot: b"generated-pdf",
        extract_pdf=lambda payload: document,
    )


@pytest.mark.parametrize(
    ("document", "expected_status", "expected_max_score", "expected_gate"),
    [
        (
            ExtractedDocument(
                text="",
                pages=(),
                page_count=1,
                has_text_layer=False,
                warnings=("page_1_has_no_text",),
            ),
            "complete",
            20,
            "PARSE-001",
        ),
        (
            ExtractedDocument(
                text="Edo Example edo@example.com",
                pages=(),
                page_count=1,
                has_text_layer=True,
            ),
            "needs_review",
            55,
            None,
        ),
    ],
)
def test_parseability_hard_gate_scenarios(
    document,
    expected_status,
    expected_max_score,
    expected_gate,
):
    result = analyze_generated_cv(
        AnalysisInput(generated_cv_id=1, profile_snapshot=PROFILE),
        dependencies(document),
    )

    assert result.status.value == expected_status
    assert result.overall.score is not None
    assert result.overall.score <= expected_max_score
    if expected_gate is not None:
        assert result.overall.hard_gate == expected_gate


def test_complete_single_column_resume_remains_authoritative():
    result = analyze_generated_cv(
        AnalysisInput(generated_cv_id=1, profile_snapshot=PROFILE),
        dependencies(
            ExtractedDocument(
                text=FULL_TEXT,
                pages=(),
                page_count=1,
                has_text_layer=True,
            )
        ),
    )

    assert result.status.value == "complete"
    assert result.overall.score is not None
    assert result.overall.score >= 75
    assert result.parseability is not None
    assert result.parseability.band in {"excellent", "good"}


def test_job_specific_analysis_without_role_match_requires_review():
    result = analyze_generated_cv(
        AnalysisInput(
            generated_cv_id=1,
            profile_snapshot=PROFILE,
            job_description=(
                "We need a backend engineer with Python and FastAPI experience "
                "to build reliable APIs and event-driven services for customers."
            ),
            role_match=None,
        ),
        dependencies(
            ExtractedDocument(
                text=FULL_TEXT,
                pages=(),
                page_count=1,
                has_text_layer=True,
            )
        ),
    )

    assert result.status.value == "needs_review"
    assert result.tailoring is not None
    assert result.tailoring.score <= 60
    assert any(rule.rule_id == "TAILOR-008" for rule in result.rule_results)
