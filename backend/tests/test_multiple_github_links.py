from app.schemas import ProfileData
from app.utils import format_profile_for_llm
from integration.template import render_cv_template


def _base_profile(**overrides) -> dict:
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": None,
        "location": None,
        "linkedin": None,
        "github": [],
        "portfolio": None,
        "summary": None,
        "work_experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "certifications": [],
    }
    payload.update(overrides)
    return payload


def test_profile_data_github_defaults_to_empty_list():
    profile = ProfileData(**_base_profile())
    assert profile.github == []


def test_profile_data_accepts_multiple_github_links():
    profile = ProfileData(
        **_base_profile(github=["https://github.com/jane-personal", "https://github.com/jane-work"])
    )
    assert profile.github == ["https://github.com/jane-personal", "https://github.com/jane-work"]


def test_format_profile_for_llm_joins_multiple_github_links():
    profile = ProfileData(
        **_base_profile(github=["https://github.com/jane-personal", "https://github.com/jane-work"])
    )
    text = format_profile_for_llm(profile)
    assert "GitHub: https://github.com/jane-personal, https://github.com/jane-work" in text


def test_format_profile_for_llm_omits_github_line_when_empty():
    profile = ProfileData(**_base_profile())
    text = format_profile_for_llm(profile)
    assert "GitHub:" not in text


def _template_profile(**overrides) -> dict:
    base = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": None,
        "location": None,
        "linkedin": None,
        "github": [],
        "portfolio": None,
        "summary": None,
        "work_experience": [],
        "education": [],
        "skills": [],
        "skill_categories": None,
        "projects": [],
        "certifications": [],
    }
    base.update(overrides)
    return base


def test_cv_template_renders_every_github_link():
    profile = _template_profile(
        github=["https://github.com/jane-personal", "https://github.com/jane-work"]
    )
    html = render_cv_template(profile)
    assert "https://github.com/jane-personal" in html
    assert "https://github.com/jane-work" in html
