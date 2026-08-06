from app.resume_readiness.domain import ExtractedDocument
from app.resume_readiness.pipeline import (
    AnalysisInput,
    PipelineDependencies,
    analyze_generated_cv,
)


def _snapshot():
    return {
        "name": "Edo Example",
        "email": "edo@example.com",
        "summary": "Backend engineer building reliable APIs.",
        "work_experience": [
            {
                "company": "Example Corp",
                "role": "Backend Engineer",
                "start_date": "2022-01",
                "end_date": "Present",
                "bullets": ["Built reliable APIs and improved latency by 20%"],
            }
        ],
        "education": [],
        "skills": ["Python"],
    }


def _dependencies(text: str | None = None):
    extracted_text = text or (
        "Edo Example edo@example.com Backend Engineer Example Corp "
        "2022-01 Present Built reliable APIs and improved latency by 20% Python"
    )
    return PipelineDependencies(
        render_pdf=lambda snapshot: b"pdf",
        extract_pdf=lambda data: ExtractedDocument(
            text=extracted_text,
            pages=(),
            page_count=1,
            has_text_layer=True,
        ),
    )


def test_general_analysis_runs_available_categories():
    result = analyze_generated_cv(
        AnalysisInput(
            generated_cv_id=42,
            profile_snapshot=_snapshot(),
        ),
        _dependencies(),
    )

    assert result.mode.value == "general"
    assert result.parseability is not None
    assert result.quality is not None
    assert result.tailoring is None
    assert result.status.value == "complete"


def test_pdf_parser_failure_returns_failed_without_score():
    def fail_extract(data: bytes):
        raise RuntimeError("parser failed")

    result = analyze_generated_cv(
        AnalysisInput(
            generated_cv_id=42,
            profile_snapshot=_snapshot(),
        ),
        PipelineDependencies(render_pdf=lambda snapshot: b"pdf", extract_pdf=fail_extract),
    )

    assert result.status.value == "failed"
    assert result.overall.score is None
    assert result.failure_code == "PDF_PARSE_FAILED"


def test_low_coverage_requires_review_and_applies_cap():
    result = analyze_generated_cv(
        AnalysisInput(
            generated_cv_id=42,
            profile_snapshot=_snapshot(),
        ),
        _dependencies("Edo Example edo@example.com"),
    )

    assert result.status.value == "needs_review"
    assert result.overall.score <= 55
    assert result.overall.hard_gate in {"PARSE-007", "PARSE-012"}


def test_image_only_resume_is_definitively_not_ready():
    result = analyze_generated_cv(
        AnalysisInput(
            generated_cv_id=42,
            profile_snapshot=_snapshot(),
        ),
        PipelineDependencies(
            render_pdf=lambda snapshot: b"pdf",
            extract_pdf=lambda data: ExtractedDocument(
                text="",
                pages=(),
                page_count=1,
                has_text_layer=False,
                warnings=("page_1_has_no_text",),
            ),
        ),
    )

    assert result.status.value == "complete"
    assert result.overall.band == "not_ready"
    assert result.overall.score <= 20
    assert result.overall.hard_gate == "PARSE-001"
