"""Cookie names and response helpers for opaque auth sessions."""

from fastapi import Response

from app.auth.service import IssuedSession

SESSION_COOKIE_NAME = "applykit_session"
CSRF_COOKIE_NAME = "applykit_csrf"


def _disable_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def set_auth_cookies(
    response: Response,
    issued: IssuedSession,
    *,
    secure: bool,
) -> None:
    _disable_caching(response)
    max_age = 30 * 24 * 60 * 60 if issued.remember_device else 7 * 24 * 60 * 60
    response.set_cookie(
        SESSION_COOKIE_NAME,
        issued.session_token,
        max_age=max_age,
        expires=issued.expires_at,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        issued.csrf_token,
        max_age=max_age,
        expires=issued.expires_at,
        path="/",
        secure=secure,
        httponly=False,
        samesite="lax",
    )


def clear_auth_cookies(response: Response, *, secure: bool) -> None:
    _disable_caching(response)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
        secure=secure,
        httponly=False,
        samesite="lax",
    )
