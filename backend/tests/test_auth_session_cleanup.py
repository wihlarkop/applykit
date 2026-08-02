from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_auth_session, revoke_session
from app.models import AuthSession, Base


def test_creating_a_session_prunes_expired_and_revoked_sessions() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)

    with factory() as db:
        revoked = create_auth_session(db, remember_device=False, now=now)
        revoke_session(db, revoked.session_token, now=now + timedelta(minutes=1))
        create_auth_session(
            db,
            remember_device=False,
            now=now + timedelta(days=8),
        )

        count = db.scalar(select(func.count(AuthSession.id)))
        assert count == 1
