import io

import pdfplumber

from app.routes import generate as generate_routes


def _profile(project_count: int) -> dict:
    long_description = (
        "A synthetic project description repeated to occupy enough vertical "
        "space that including all of these projects pushes the resume past "
        "a single page during the test. "
    ) * 12
    return {
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
        "projects": [
            {
                "name": f"Project {i}",
                "description": long_description,
                "tech_stack": ["Python"],
                "link": None,
            }
            for i in range(project_count)
        ],
        "certifications": [],
    }


def _page_count(pdf_bytes: bytes) -> int:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return len(pdf.pages)


def test_render_cv_pdf_keeps_all_projects_when_they_fit_one_page():
    response = generate_routes._render_cv_pdf(_profile(project_count=2))

    assert _page_count(response.body) == 1


def _content_bottom(pdf_bytes: bytes) -> float:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        words = pdf.pages[0].extract_words()
        return max(w["bottom"] for w in words)


def test_render_cv_pdf_stretches_spacing_when_page_has_slack():
    profile = _profile(project_count=0)
    profile["work_experience"] = [
        {
            "company": "Acme",
            "role": "Engineer",
            "start_date": "2022",
            "end_date": None,
            "bullets": ["Did a thing.", "Did another thing."],
        }
    ]

    base_pdf = generate_routes.html_to_pdf(generate_routes.render_cv_template(profile))
    assert _page_count(base_pdf) == 1

    response = generate_routes._render_cv_pdf(profile)

    assert _page_count(response.body) == 1
    assert _content_bottom(response.body) > _content_bottom(base_pdf)


def _many_short_projects_profile(project_count: int) -> dict:
    # Many short (margin-dominated) items reach a fit tight enough that the
    # spacing estimate's probe render overflows, exercising the bisection fallback.
    return {
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
        "projects": [
            {
                "name": f"Project {i}",
                "description": "Short desc.",
                "tech_stack": ["Python"],
                "link": None,
            }
            for i in range(project_count)
        ],
        "certifications": [],
    }


def test_render_cv_pdf_falls_back_when_spacing_probe_overflows():
    profile = _many_short_projects_profile(project_count=52)

    base_pdf = generate_routes.html_to_pdf(generate_routes.render_cv_template(profile))
    assert _page_count(base_pdf) == 1, "fixture must fit one page at the base scale"

    probe_document = generate_routes.html_to_document(
        generate_routes.render_cv_template(
            profile, spacing_scale=generate_routes.SPACING_PROBE_SCALE
        )
    )
    assert len(probe_document.pages) > 1, (
        "fixture must overflow at the probe scale for this test to exercise "
        "the bisection fallback"
    )

    response = generate_routes._render_cv_pdf(profile)

    assert _page_count(response.body) == 1


def test_render_cv_pdf_trims_to_top_projects_when_they_would_overflow():
    profile = _profile(project_count=8)

    unrimmed_html = generate_routes.render_cv_template(profile)
    assert _page_count(generate_routes.html_to_pdf(unrimmed_html)) > 1, (
        "test fixture must actually overflow one page before trimming for "
        "this test to prove anything"
    )

    response = generate_routes._render_cv_pdf(profile)

    assert _page_count(response.body) == 1
    with pdfplumber.open(io.BytesIO(response.body)) as pdf:
        text = pdf.pages[0].extract_text()
    kept = [f"Project {i}" for i in range(generate_routes.MAX_PROJECTS_WHEN_TRIMMED)]
    dropped = [
        f"Project {i}"
        for i in range(generate_routes.MAX_PROJECTS_WHEN_TRIMMED, 8)
    ]
    assert all(name in text for name in kept)
    assert not any(name in text for name in dropped)
