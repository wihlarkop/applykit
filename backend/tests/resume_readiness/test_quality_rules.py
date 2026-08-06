from app.resume_readiness.domain import RuleOutcome
from app.resume_readiness.rules_quality import evaluate_quality


def test_duplicate_bullets_are_reported_once_with_locations():
    snapshot = {
        "name": "Edo",
        "email": "edo@example.com",
        "summary": "Backend engineer",
        "work_experience": [
            {
                "company": "A",
                "role": "Engineer",
                "bullets": ["Built APIs", "Built APIs"],
            }
        ],
        "education": [],
        "skills": ["Python"],
    }

    results = evaluate_quality(snapshot=snapshot, extracted=None)

    duplicate = next(result for result in results if result.rule_id == "QUALITY-008")
    assert duplicate.evidence["duplicate_count"] == 2
    assert len(duplicate.locations) == 2


def test_missing_summary_is_advisory_not_critical():
    results = evaluate_quality(
        snapshot={
            "name": "Edo",
            "email": "edo@example.com",
            "summary": "",
            "work_experience": [],
            "education": [],
            "skills": [],
        },
        extracted=None,
    )

    rule = next(result for result in results if result.rule_id == "QUALITY-003")
    assert rule.severity.value == "improvement"
    assert rule.score_cap is None


def test_reverse_chronological_experience_and_present_use_one_date_style():
    results = evaluate_quality(
        snapshot={
            "name": "Edo",
            "email": "edo@example.com",
            "summary": "Backend engineer",
            "work_experience": [
                {
                    "company": "Recent",
                    "role": "Senior Engineer",
                    "start_date": "2024-01",
                    "end_date": "Present",
                    "bullets": ["Built reliable APIs for customers"],
                },
                {
                    "company": "Older",
                    "role": "Engineer",
                    "start_date": "2020-01",
                    "end_date": "2023-12",
                    "bullets": ["Improved service performance by 20%"],
                },
            ],
            "education": [],
            "skills": ["Python"],
        },
        extracted=None,
    )

    assert not any(result.rule_id == "QUALITY-004" for result in results)
    assert not any(result.rule_id == "QUALITY-005" for result in results)


def test_core_empty_sections_cap_quality():
    results = evaluate_quality(
        snapshot={
            "name": "Edo",
            "email": "edo@example.com",
            "summary": "",
            "work_experience": [],
            "education": [],
            "skills": [],
        },
        extracted=None,
    )

    rule = next(result for result in results if result.rule_id == "QUALITY-013")
    assert rule.outcome == RuleOutcome.FAIL
    assert rule.score_cap == 59
