from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, LlmUsageLog
from app.routes.usage import get_llm_usage


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _usage(created_at: datetime, total_tokens: int = 1) -> LlmUsageLog:
    return LlmUsageLog(
        created_at=created_at,
        operation="cv_generation",
        provider="openai",
        model="gpt-4.1-mini",
        total_tokens=total_tokens,
        success=True,
    )


def test_date_to_includes_the_entire_selected_day():
    db = _make_session()
    try:
        db.add_all(
            [
                _usage(datetime(2026, 7, 30, 23, 59, 59)),
                _usage(datetime(2026, 7, 31, 0, 0, 0)),
            ]
        )
        db.commit()

        response = get_llm_usage(date_to=date(2026, 7, 30), db=db)

        assert response.total == 1
        assert response.items[0].created_at == datetime(2026, 7, 30, 23, 59, 59)
    finally:
        db.close()


def test_usage_totals_include_more_than_ten_thousand_rows():
    db = _make_session()
    try:
        db.bulk_save_objects(
            [_usage(datetime(2026, 7, 30, 12, 0, 0)) for _ in range(10_001)]
        )
        db.commit()

        response = get_llm_usage(limit=1, db=db)

        assert response.total == 10_001
        assert response.total_tokens == 10_001
        assert len(response.items) == 1
    finally:
        db.close()
