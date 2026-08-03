from app.models import Profile
from app.readiness.profile import evaluate_profile


def make_profile(**overrides) -> Profile:
    values = {
        "id": 1,
        "label": "Default",
        "color": "#6366f1",
        "icon": "💼",
        "name": "",
        "email": "",
        "summary": None,
        "work_experience": "[]",
        "education": "[]",
        "skills": "[]",
        "projects": "[]",
        "certifications": "[]",
    }
    values.update(overrides)
    return Profile(**values)


def test_profile_ready_requires_name_email_history_and_skill() -> None:
    result = evaluate_profile(
        make_profile(
            name="Wihlarko",
            email="w@example.com",
            work_experience='[{"company":"X","role":"Engineer"}]',
            skills='["Python"]',
        )
    )

    assert result.ready is True
    assert result.missing_requirements == []


def test_education_can_satisfy_history_requirement() -> None:
    result = evaluate_profile(
        make_profile(
            name="Wihlarko",
            email="w@example.com",
            education='[{"institution":"University"}]',
            skills='["Python"]',
        )
    )

    assert result.ready is True


def test_empty_or_invalid_json_is_not_ready_and_does_not_crash() -> None:
    result = evaluate_profile(
        make_profile(
            name="Wihlarko",
            email="w@example.com",
            work_experience="{",
            education=None,
            skills="null",
        )
    )

    assert result.ready is False
    assert "experience_or_education" in result.missing_requirements
    assert "skills" in result.missing_requirements


def test_completeness_is_deterministic_and_capped_at_100() -> None:
    result = evaluate_profile(
        make_profile(
            name="Wihlarko",
            email="w@example.com",
            summary="Senior engineer",
            work_experience='[{"company":"X","role":"Engineer"}]',
            education='[{"institution":"University"}]',
            skills='["Python"]',
            projects='[{"name":"ApplyKit"}]',
            certifications='[{"name":"Cloud"}]',
        )
    )

    assert result.completeness == 100
    assert result.ready is True


def test_recommendations_are_advisory_only() -> None:
    result = evaluate_profile(
        make_profile(
            name="Wihlarko",
            email="w@example.com",
            work_experience='[{"company":"X","role":"Engineer"}]',
            skills='["Python"]',
        )
    )

    assert result.ready is True
    assert "Add a professional summary." in result.recommendations
    assert "Add one or more relevant projects." in result.recommendations
