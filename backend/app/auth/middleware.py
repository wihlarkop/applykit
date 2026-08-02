"""ASGI middleware enforcing optional single-owner authentication."""

from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.auth.cookies import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, clear_auth_cookies
from app.auth.service import authenticate_session, validate_csrf_token
from app.config import Settings, get_settings
from app.database import SessionLocal
from app.exceptions.auth import (
    AuthenticationForbiddenError,
    AuthenticationRequiredError,
)
from app.exceptions.base import AppError

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PUBLIC_PATHS = {
    "/health",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/setup",
}
API_DOCUMENTATION_PATHS = {"/docs", "/redoc", "/openapi.json"}


def _error_response(error: AppError) -> JSONResponse:
    headers = {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        **error.headers,
    }
    return JSONResponse(
        status_code=error.status_code,
        content=error.to_envelope().model_dump(mode="json"),
        headers=headers,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Require a valid server-side session for protected-mode requests."""

    def __init__(
        self,
        app: Any,
        *,
        settings: Settings | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()
        self.session_factory = session_factory or SessionLocal

    def _origin_allowed(self, origin: str | None) -> bool:
        if not origin:
            return False
        return "*" in self.settings.cors_origins or origin in self.settings.cors_origins

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request.state.auth_settings = self.settings
        request.state.authenticated = self.settings.auth_mode == "disabled"
        request.state.auth_session_id = None
        request.state.auth_session_expires_at = None
        request.state.auth_session_remember_device = False

        if self.settings.auth_mode == "disabled":
            return await call_next(request)

        # When documentation is disabled, allow FastAPI to return a real 404
        # rather than turning an absent route into an authentication challenge.
        if (
            not self.settings.debug
            and request.url.path in API_DOCUMENTATION_PATHS
        ):
            return await call_next(request)

        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        is_public = request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS

        with self.session_factory() as db:
            auth_session = authenticate_session(db, session_token)
            if auth_session is not None:
                request.state.authenticated = True
                request.state.auth_session_id = auth_session.id
                request.state.auth_session_expires_at = auth_session.expires_at
                request.state.auth_session_remember_device = bool(
                    auth_session.remember_device
                )

            if not is_public:
                if auth_session is None:
                    response = _error_response(AuthenticationRequiredError())
                    if session_token:
                        clear_auth_cookies(
                            response,
                            secure=self.settings.cookie_secure,
                        )
                    return response

                if request.method not in SAFE_METHODS:
                    origin = request.headers.get("origin")
                    csrf_header = request.headers.get("x-csrf-token")
                    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
                    if (
                        not self._origin_allowed(origin)
                        or not csrf_header
                        or not csrf_cookie
                        or csrf_header != csrf_cookie
                        or not validate_csrf_token(auth_session, csrf_header)
                    ):
                        return _error_response(AuthenticationForbiddenError())

        return await call_next(request)
