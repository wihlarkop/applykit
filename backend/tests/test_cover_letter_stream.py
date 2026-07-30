import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, GeneratedCoverLetter, Profile
from app.routes import generate as generate_routes
from app.schemas import CoverLetterRequest


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_cover_letter_is_persisted_before_done_event(monkeypatch):
    """The done event must mean history is already durable."""
    db = _make_session()
    profile = Profile(name="Jane Doe", email="jane@example.com")
    db.add(profile)
    db.commit()

    async def fake_stream_llm(*args, **kwargs):
        yield "Generated cover letter"

    monkeypatch.setattr(generate_routes, "stream_llm", fake_stream_llm)

    request = CoverLetterRequest(
        profile_id=profile.id,
        job_description="Backend engineer role",
        company_name="Example Corp",
    )

    async def consume_until_done():
        stream = generate_routes.generate_cover_letter(
            request,
            db=db,
            llm=("openai/test-model", "test-key"),
        )
        try:
            await anext(stream)  # token
            await anext(stream)  # done

            entry = db.query(GeneratedCoverLetter).one_or_none()
            assert entry is not None
            assert entry.cover_letter_text == "Generated cover letter"
        finally:
            await stream.aclose()

    try:
        asyncio.run(consume_until_done())
    finally:
        db.close()
