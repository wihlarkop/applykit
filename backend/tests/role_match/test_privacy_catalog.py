from app.role_match.evidence_catalog import build_evidence_catalog
from app.role_match.privacy import build_safe_profile
from app.schemas import ProfileData


def make_profile(**updates) -> ProfileData:
    payload = {
        "name": "Candidate A",
        "email": "a@example.com",
        "phone": "+62 812",
        "location": "Jakarta, Indonesia",
        "linkedin": "https://linkedin.example/a",
        "github": "https://github.example/a",
        "portfolio": "https://portfolio.example/a",
        "summary": "Backend engineer",
        "work_experience": [
            {
                "company": "Example",
                "role": "Backend Engineer",
                "start_date": "2023-01",
                "end_date": None,
                "bullets": ["Built asynchronous services using Google Pub/Sub."],
            }
        ],
        "education": [],
        "skills": ["Python", "FastAPI"],
        "projects": [],
        "certifications": [],
    }
    payload.update(updates)
    return ProfileData(**payload)


def test_safe_profile_excludes_identity_and_contact_fields() -> None:
    safe = build_safe_profile(make_profile(), include_location=False)
    serialized = safe.model_dump_json()
    for forbidden in [
        "Candidate A",
        "a@example.com",
        "+62 812",
        "linkedin.example",
        "github.example",
        "portfolio.example",
        "Jakarta",
    ]:
        assert forbidden not in serialized


def test_name_and_contact_changes_do_not_change_catalog() -> None:
    first = build_evidence_catalog(build_safe_profile(make_profile(), False))
    second = build_evidence_catalog(
        build_safe_profile(
            make_profile(name="Candidate B", email="b@example.com", phone="000"),
            False,
        )
    )
    assert first == second


def test_location_is_only_included_when_job_related() -> None:
    profile = make_profile()
    assert build_safe_profile(profile, include_location=False).location is None
    assert build_safe_profile(profile, include_location=True).location == "Jakarta, Indonesia"


def test_catalog_uses_stable_ids_and_source_hierarchy() -> None:
    catalog = build_evidence_catalog(build_safe_profile(make_profile(), False))
    assert [item.evidence_id for item in catalog] == [
        "summary:0",
        "work:0:role",
        "work:0:bullet:0",
        "skill:python",
        "skill:fastapi",
    ]
