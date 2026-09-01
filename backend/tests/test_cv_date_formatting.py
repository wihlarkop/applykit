from integration.template import format_date_range, render_cv_template


def _profile(**overrides) -> dict:
    base = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": None,
        "location": None,
        "linkedin": None,
        "github": None,
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


def test_format_date_range_hides_missing_start_and_end():
    assert format_date_range(None, None) == ""
    assert format_date_range("", "") == ""


def test_format_date_range_omits_dash_when_only_end_present():
    assert format_date_range(None, "Jun 2022") == "Jun 2022"


def test_format_date_range_defaults_missing_end_to_present():
    assert format_date_range("Sep 2018", None) == "Sep 2018 – Present"


def test_format_date_range_renders_full_range():
    assert format_date_range("Sep 2018", "Jun 2022") == "Sep 2018 – Jun 2022"


def test_cv_template_never_renders_the_literal_string_none():
    profile = _profile(
        work_experience=[
            {
                "role": "Engineer",
                "company": "Acme",
                "start_date": None,
                "end_date": None,
                "bullets": [],
            },
        ],
        education=[
            {
                "institution": "State University",
                "degree": "BS",
                "field": "Computer Science",
                "start_date": None,
                "end_date": "Jun 2016",
            },
        ],
        certifications=[
            {"name": "AWS Certified", "issuer": "Amazon", "date": None},
        ],
    )

    html = render_cv_template(profile)

    assert "None" not in html
    assert "Jun 2016" in html
