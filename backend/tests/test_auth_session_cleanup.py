from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_auth_session, revoke_session
from app.models import AuthSession, Base


def test_creating_a_session_prunes_inactive_rows_without_reusing_ids() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    now = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)

    with factory() as db:
        revoked = create_auth_session(db, remember_device=False, now=now)
        revoked_row = db.scalar(
            select(AuthSession).where(
                AuthSession.token_hash.is_not(None),
            )
        )
        assert revoked_row is not None
        revoked_id = revoked_row.id

        revoke_session(db, revoked.session_token, now=now + timedelta(minutes=1))
        current = create_auth_session(
            db,
            remember_device=False,
            now=now + timedelta(days=8),
        )
        current_row = db.scalar(
            select(AuthSession).where(AuthSession.token_hash.is_not(None))
        )

        assert current_row is not None
        assert current_row.id > revoked_id
        assert current.session_token != revoked.session_token
        assert db.scalar(select(func.count(AuthSession.id))) == 1
