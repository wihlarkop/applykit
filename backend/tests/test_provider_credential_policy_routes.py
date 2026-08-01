from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.credential_schemas import UpdateCredentialPolicyRequest
from app.models import Base
from app.routes.settings import get_credential_policy_route, update_credential_policy_route


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_policy_defaults_to_manual_with_two_max_attempts():
    db = _make_session()
    try:
        policy = get_credential_policy_route("openai", db)
        assert policy.strategy == "manual"
        assert policy.max_attempts == 2
    finally:
        db.close()


def test_policy_can_enable_failover_and_round_robin():
    db = _make_session()
    try:
        failover = update_credential_policy_route(
            "openai",
            UpdateCredentialPolicyRequest(strategy="failover", max_attempts=2),
            db,
        )
        assert failover.strategy == "failover"

        round_robin = update_credential_policy_route(
            "openai",
            UpdateCredentialPolicyRequest(strategy="round_robin", max_attempts=3),
            db,
        )
        assert round_robin.strategy == "round_robin"
        assert round_robin.max_attempts == 3
    finally:
        db.close()
