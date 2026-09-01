import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, GeneratedCV, Profile
from app.routes import generate as generate_routes
from app.schemas import GenerateCvRequest


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _add_profile(db):
    profile = Profile(name="Jane Doe", email="jane@example.com")
    db.add(profile)
    db.commit()
    return profile


def _configure_keyless_llm(monkeypatch):
    monkeypatch.setattr(
        generate_routes,
        "_get_llm_config_raw",
        lambda db: ("ollama/llama3.2", ""),
    )
    monkeypatch.setattr(
        generate_routes,
        "call_llm",
        lambda *args, **kwargs: '{"summary":"Enhanced summary","work_experience":[]}',
    )


def test_sync_cv_enhancement_runs_for_keyless_provider(monkeypatch):
    """Optional enhancement uses provider readiness rather than secret presence."""
    db = _make_session()
    try:
        profile = _add_profile(db)
        _configure_keyless_llm(monkeypatch)

        response = generate_routes.generate_cv(
            GenerateCvRequest(profile_id=profile.id, enhance=True),
            db,
        )

        assert response.enhanced is True
        assert response.profile.summary == "Enhanced summary"
        assert db.query(GeneratedCV).one().enhanced == 1
    finally:
        db.close()


def test_streaming_cv_enhancement_runs_for_keyless_provider(monkeypatch):
    """The SSE path follows the same provider-readiness rule."""
    db = _make_session()
    try:
        profile = _add_profile(db)
        _configure_keyless_llm(monkeypatch)

        async def consume_stream():
            return [
                event
                async for event in generate_routes.generate_cv_stream(
                    GenerateCvRequest(profile_id=profile.id, enhance=True),
                    db,
                )
            ]

        events = asyncio.run(consume_stream())

        assert len(events) == 2
        assert db.query(GeneratedCV).one().enhanced == 1
    finally:
        db.close()


def test_cv_enhancement_applies_reordered_projects_and_skill_categories(monkeypatch):
    """When the LLM returns projects/skill_categories, they replace the originals."""
    db = _make_session()
    try:
        profile = _add_profile(db)
        profile.projects = (
            '[{"name":"A","description":"d","tech_stack":[],"link":null},'
            '{"name":"B","description":"d","tech_stack":[],"link":null}]'
        )
        db.commit()

        monkeypatch.setattr(
            generate_routes,
            "_get_llm_config_raw",
            lambda db: ("ollama/llama3.2", ""),
        )
        monkeypatch.setattr(
            generate_routes,
            "call_llm",
            lambda *args, **kwargs: (
                '{"summary":"s","work_experience":[],'
                '"projects":[{"name":"B","description":"d","tech_stack":[],"link":null},'
                '{"name":"A","description":"d","tech_stack":[],"link":null}],'
                '"skill_categories":[{"label":"Core","skills":["Python"]}]}'
            ),
        )

        response = generate_routes.generate_cv(
            GenerateCvRequest(profile_id=profile.id, enhance=True),
            db,
        )

        assert [p.name for p in response.profile.projects] == ["B", "A"]
        assert [c.model_dump() for c in response.profile.skill_categories] == [
            {"label": "Core", "skills": ["Python"]}
        ]
    finally:
        db.close()


def test_cv_enhancement_falls_back_to_original_projects_when_llm_omits_them(
    monkeypatch,
):
    """An LLM response with no projects/skill_categories keeps the original order."""
    db = _make_session()
    try:
        profile = _add_profile(db)
        profile.projects = (
            '[{"name":"A","description":"d","tech_stack":[],"link":null}]'
        )
        db.commit()
        _configure_keyless_llm(monkeypatch)

        response = generate_routes.generate_cv(
            GenerateCvRequest(profile_id=profile.id, enhance=True),
            db,
        )

        assert [p.name for p in response.profile.projects] == ["A"]
        assert response.profile.skill_categories is None
    finally:
        db.close()
