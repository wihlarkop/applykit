from app.resume_readiness.coverage import calculate_source_coverage


def test_coverage_marks_source_experience_as_present():
    snapshot = {
        "name": "Edo Example",
        "email": "edo@example.com",
        "work_experience": [
            {
                "company": "Example Corp",
                "role": "Backend Engineer",
                "bullets": ["Built event-driven services with Pub/Sub"],
            }
        ],
        "education": [],
        "skills": ["Python", "FastAPI"],
    }
    extracted = (
        "Edo Example edo@example.com Backend Engineer Example Corp "
        "Built event-driven services with Pub/Sub Python FastAPI"
    )

    result = calculate_source_coverage(snapshot, extracted)

    assert result.coverage >= 0.95
    assert result.missing_critical == ()


def test_coverage_reports_missing_critical_experience():
    snapshot = {
        "name": "Edo Example",
        "email": "edo@example.com",
        "work_experience": [
            {"company": "Example Corp", "role": "Backend Engineer", "bullets": []}
        ],
        "education": [],
        "skills": [],
    }

    result = calculate_source_coverage(snapshot, "Edo Example edo@example.com")

    assert "experience:0:role" in result.missing_critical
    assert "experience:0:company" in result.missing_critical
