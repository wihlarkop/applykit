from collections.abc import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.middleware import AuthMiddleware
from app.auth.service import issue_setup_token
from app.config import Settings
from app.database import get_db
from app.exceptions.handlers import exception_handlers
from app.models import Base
from app.routes import auth


def _make_app(
    auth_mode: str = "password",
    *,
    debug: bool = False,
) -> tuple[FastAPI, sessionmaker, str | None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    settings = Settings(
        database_url="sqlite:///:memory:",
        auth_mode=auth_mode,
        cookie_secure=False,
        cors_origins=["http://testserver"],
        debug=debug,
    )

    app = FastAPI(
        exception_handlers=exception_handlers,
        docs_url="/docs" if debug else None,
        redoc_url="/redoc" if debug else None,
        openapi_url="/openapi.json" if debug else None,
    )
    app.add_middleware(
        AuthMiddleware,
        settings=settings,
        session_factory=factory,
    )
    app.include_router(auth.router, prefix="/api")

    def override_db() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/private")
    def private() -> dict[str, str]:
        return {"status": "private"}

    @app.post("/api/private")
    def mutate() -> dict[str, str]:
        return {"status": "changed"}

    setup_token = None
    if auth_mode == "password":
        with factory() as db:
            setup_token = issue_setup_token(db)

    return app, factory, setup_token


def _setup_owner(client: TestClient, setup_token: str) -> None:
    response = client.post(
        "/api/auth/setup",
        headers={"Origin": "http://testserver"},
        json={
            "setup_token": setup_token,
            "password": "correct horse battery staple",
            "display_name": "Owner",
        },
    )
    assert response.status_code == 201


def test_password_mode_exposes_only_health_and_auth_setup_before_login() -> None:
    app, _, setup_token = _make_app()
    assert setup_token is not None

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        status = client.get("/api/auth/status")
        assert status.status_code == 200
        assert status.json() == {
            "auth_mode": "password",
            "setup_required": True,
            "authenticated": False,
            "session_expires_at": None,
        }
        private = client.get("/api/private")
        assert private.status_code == 401
        assert private.json()["error"]["code"] == "AUTH_REQUIRED"


def test_public_setup_requires_an_explicit_allowed_origin() -> None:
    app, _, setup_token = _make_app()
    assert setup_token is not None
    payload = {
        "setup_token": setup_token,
        "password": "correct horse battery staple",
    }

    with TestClient(app) as client:
        missing = client.post("/api/auth/setup", json=payload)
        assert missing.status_code == 403
        assert missing.json()["error"]["code"] == "AUTH_FORBIDDEN"

        wrong = client.post(
            "/api/auth/setup",
            headers={"Origin": "http://evil.example"},
            json=payload,
        )
        assert wrong.status_code == 403

        allowed = client.post(
            "/api/auth/setup",
            headers={"Origin": "http://testserver"},
            json=payload,
        )
        assert allowed.status_code == 201


def test_owner_setup_creates_session_and_setup_token_is_one_time() -> None:
    app, _, setup_token = _make_app()
    assert setup_token is not None

    with TestClient(app) as client:
        _setup_owner(client, setup_token)

        assert client.cookies.get("applykit_session")
        assert client.cookies.get("applykit_csrf")
        assert client.get("/api/private").status_code == 200
        assert client.get("/api/auth/status").json()["authenticated"] is True

        replay = client.post(
            "/api/auth/setup",
            headers={"Origin": "http://testserver"},
            json={
                "setup_token": setup_token,
                "password": "another secure passphrase",
            },
        )
        assert replay.status_code == 409


def test_mutating_requests_require_matching_csrf_header_and_origin() -> None:
    app, _, setup_token = _make_app()
    assert setup_token is not None

    with TestClient(app) as client:
        _setup_owner(client, setup_token)
        csrf_token = client.cookies.get("applykit_csrf")
        assert csrf_token

        assert client.post("/api/private").status_code == 403
        assert (
            client.post(
                "/api/private",
                headers={
                    "Origin": "http://evil.example",
                    "X-CSRF-Token": csrf_token,
                },
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/private",
                headers={
                    "Origin": "http://testserver",
                    "X-CSRF-Token": csrf_token,
                },
            ).status_code
            == 200
        )


def test_logout_revokes_current_session_and_clears_cookies() -> None:
    app, _, setup_token = _make_app()
    assert setup_token is not None

    with TestClient(app) as client:
        _setup_owner(client, setup_token)
        csrf_token = client.cookies.get("applykit_csrf")
        response = client.post(
            "/api/auth/logout",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf_token,
            },
        )

        assert response.status_code == 204
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/private").status_code == 401
        assert client.cookies.get("applykit_session") is None
        assert client.cookies.get("applykit_csrf") is None


def test_login_supports_seven_and_thirty_day_absolute_sessions() -> None:
    app, _, setup_token = _make_app()
    assert setup_token is not None

    with TestClient(app) as client:
        _setup_owner(client, setup_token)
        csrf_token = client.cookies.get("applykit_csrf")
        client.post(
            "/api/auth/logout",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf_token,
            },
        )

        response = client.post(
            "/api/auth/login",
            headers={"Origin": "http://testserver"},
            json={
                "password": "correct horse battery staple",
                "remember_device": True,
            },
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["authenticated"] is True
        assert response.json()["remember_device"] is True


def test_change_password_keeps_rotated_current_session_and_revokes_others() -> None:
    app, _, setup_token = _make_app()
    assert setup_token is not None

    with TestClient(app) as first, TestClient(app) as second:
        _setup_owner(first, setup_token)
        second.post(
            "/api/auth/login",
            headers={"Origin": "http://testserver"},
            json={
                "password": "correct horse battery staple",
                "remember_device": False,
            },
        )

        csrf_token = first.cookies.get("applykit_csrf")
        response = first.post(
            "/api/auth/change-password",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf_token,
            },
            json={
                "current_password": "correct horse battery staple",
                "new_password": "a stronger replacement passphrase",
            },
        )

        assert response.status_code == 200
        assert first.get("/api/private").status_code == 200
        assert second.get("/api/private").status_code == 401


def test_security_summary_and_sign_out_other_devices() -> None:
    app, _, setup_token = _make_app()
    assert setup_token is not None

    with TestClient(app) as first, TestClient(app) as second:
        _setup_owner(first, setup_token)
        second.post(
            "/api/auth/login",
            headers={"Origin": "http://testserver"},
            json={
                "password": "correct horse battery staple",
                "remember_device": False,
            },
        )

        assert first.get("/api/auth/security").json() == {"other_sessions": 1}
        csrf_token = first.cookies.get("applykit_csrf")
        response = first.post(
            "/api/auth/sessions/revoke-others",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf_token,
            },
        )
        assert response.json() == {"revoked_sessions": 1}
        assert second.get("/api/private").status_code == 401


def test_api_documentation_follows_debug_and_auth_rules() -> None:
    protected_app, _, _ = _make_app(debug=False)
    debug_protected_app, _, setup_token = _make_app(debug=True)
    debug_local_app, _, _ = _make_app(auth_mode="disabled", debug=True)
    assert setup_token is not None

    with TestClient(protected_app) as protected:
        assert protected.get("/docs").status_code == 404
        assert protected.get("/redoc").status_code == 404
        assert protected.get("/openapi.json").status_code == 404

    with TestClient(debug_protected_app) as debug_protected:
        assert debug_protected.get("/docs").status_code == 401
        _setup_owner(debug_protected, setup_token)
        assert debug_protected.get("/docs").status_code == 200
        assert debug_protected.get("/openapi.json").status_code == 200

    with TestClient(debug_local_app) as debug_local:
        assert debug_local.get("/docs").status_code == 200
        assert debug_local.get("/openapi.json").status_code == 200


def test_disabled_mode_never_requires_owner_or_session() -> None:
    app, _, _ = _make_app(auth_mode="disabled")

    with TestClient(app) as client:
        assert client.get("/api/private").status_code == 200
        assert client.post("/api/private").status_code == 200
        assert client.get("/api/auth/status").json() == {
            "auth_mode": "disabled",
            "setup_required": False,
            "authenticated": True,
            "session_expires_at": None,
        }
