from app.schemas import Education, ProfileData
from integration.template import render_cv_template


def test_education_accomplishments_defaults_to_empty_list():
    edu = Education(institution="State University")
    assert edu.accomplishments == []


def test_education_accomplishments_accepts_a_list():
    edu = Education(institution="State University", accomplishments=["Dean's List"])
    assert edu.accomplishments == ["Dean's List"]


def test_profile_data_backfills_accomplishments_for_records_stored_before_this_field_existed():
    """Existing profiles' stored JSON won't have an "accomplishments" key -
    parsing must not fail and must default to an empty list."""
    raw_education = [
        {
            "institution": "State University",
            "degree": "BS",
            "field": "Computer Science",
            "start_date": "Sep 2014",
            "end_date": "Jun 2018",
        }
    ]
    profile = ProfileData(name="Jane Doe", email="jane@example.com", education=raw_education)
    assert profile.education[0].accomplishments == []


def _profile(**overrides) -> dict:
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


def test_cv_template_renders_education_accomplishments():
    profile = _profile(
        education=[
            {
                "institution": "State University",
                "degree": "BS",
                "field": "Computer Science",
                "start_date": "Sep 2014",
                "end_date": "Jun 2018",
                "accomplishments": ["Dean's List, all semesters", "Best Capstone Project Award"],
            },
        ],
    )

    html = render_cv_template(profile)

    # Autoescape turns the apostrophe into an HTML entity - that's correct behavior.
    assert "Dean&#39;s List, all semesters" in html
    assert "Best Capstone Project Award" in html
    assert 'class="edu-accomplishments"' in html


def test_cv_template_omits_accomplishments_list_when_empty():
    profile = _profile(
        education=[
            {
                "institution": "State University",
                "degree": "BS",
                "field": "Computer Science",
                "start_date": "Sep 2014",
                "end_date": "Jun 2018",
                "accomplishments": [],
            },
        ],
    )

    html = render_cv_template(profile)

    assert 'class="edu-accomplishments"' not in html
