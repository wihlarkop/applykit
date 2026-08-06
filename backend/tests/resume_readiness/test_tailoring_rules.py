from app.resume_readiness.rules_tailoring import evaluate_tailoring


LONG_JOB = (
    "We are hiring a backend engineer to build reliable services. "
    "The role requires Python, API design, event-driven architecture, and clear communication."
)


def test_supported_essential_requirement_missing_from_resume():
    role_match = {
        "state": "success",
        "show_authoritative_score": True,
        "requirements": [
            {
                "canonical_text": "Python",
                "importance": "critical",
                "primary_category": "essential_qualifications",
                "match_level": "strong",
                "excluded": False,
            }
        ],
    }

    results = evaluate_tailoring(
        snapshot={
            "name": "Edo",
            "email": "edo@example.com",
            "summary": "Backend engineer",
            "work_experience": [],
            "skills": [],
        },
        job_snapshot=LONG_JOB,
        role_match=role_match,
    )

    rule = next(result for result in results if result.rule_id == "TAILOR-001")
    assert rule.outcome.value == "fail"


def test_unsupported_keyword_is_critical():
    results = evaluate_tailoring(
        snapshot={
            "name": "Edo",
            "email": "edo@example.com",
            "summary": "Senior Kubernetes platform architect",
            "work_experience": [],
            "skills": ["Kubernetes"],
        },
        job_snapshot=LONG_JOB,
        role_match={
            "state": "success",
            "show_authoritative_score": True,
            "requirements": [
                {
                    "canonical_text": "Kubernetes",
                    "importance": "critical",
                    "primary_category": "essential_qualifications",
                    "match_level": "no_evidence",
                    "excluded": False,
                }
            ],
        },
    )

    rule = next(result for result in results if result.rule_id == "TAILOR-004")
    assert rule.severity.value == "critical"
    assert rule.score_cap == 60


def test_no_job_excludes_tailoring():
    results = evaluate_tailoring(
        snapshot={"name": "Edo", "email": "edo@example.com"},
        job_snapshot=None,
        role_match=None,
    )

    assert results[0].rule_id == "TAILOR-009"
    assert results[0].outcome.value == "excluded"


def test_non_authoritative_role_match_requires_review():
    results = evaluate_tailoring(
        snapshot={"name": "Edo", "email": "edo@example.com"},
        job_snapshot=LONG_JOB,
        role_match={
            "state": "needs_review",
            "show_authoritative_score": False,
            "requirements": [],
        },
    )

    assert results[0].rule_id == "TAILOR-008"
    assert results[0].requires_review is True
