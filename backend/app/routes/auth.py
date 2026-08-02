"""HTTP endpoints for optional single-owner Community authentication."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.cookies import SESSION_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.auth.passwords import PasswordValidationError
from app.auth.schemas import (
    AuthenticatedSessionResponse,
    AuthStatusResponse,
    ChangePasswordRequest,
    LoginRequest,
    OwnerSetupRequest,
    RevokeSessionsResponse,
    SecuritySummaryResponse,
)
from app.auth.service import (
    AuthenticationLocked,
    InvalidCredentials,
    OwnerAlreadyConfigured,
    change_owner_password,
    check_authentication_allowed,
    complete_owner_setup,
    create_auth_session,
    owner_exists,
    record_login_failure,
    record_login_success,
    revoke_other_sessions,
    revoke_session,
    security_summary,
    verify_owner_password,
)
from app.config import Settings, get_settings
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _settings(request: Request) -> Settings:
    return getattr(request.state, "auth_settings", get_settings())


def _origin_allowed(request: Request, settings: Settings) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    return "*" in settings.cors_origins or origin in settings.cors_origins


def _require_public_origin(request: Request, settings: Settings) -> None:
    if not _origin_allowed(request, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request verification failed.",
        )


def _locked_error(exc: AuthenticationLocked) -> HTTPException:
    now = datetime.now(UTC)
    retry_after = max(1, int((exc.locked_until - now).total_seconds()))
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many attempts. Try again later.",
        headers={"Retry-After": str(retry_after)},
    )


def _session_response(issued) -> AuthenticatedSessionResponse:
    return AuthenticatedSessionResponse(
        authenticated=True,
        remember_device=issued.remember_device,
        session_expires_at=issued.expires_at,
    )


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(request: Request, db: Session = Depends(get_db)) -> AuthStatusResponse:
    settings = _settings(request)
    if settings.auth_mode == "disabled":
        return AuthStatusResponse(
            auth_mode="disabled",
            setup_required=False,
            authenticated=True,
            session_expires_at=None,
        )

    configured = owner_exists(db)
    authenticated = bool(getattr(request.state, "authenticated", False))
    expires_at = getattr(request.state, "auth_session_expires_at", None)
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return AuthStatusResponse(
        auth_mode="password",
        setup_required=not configured,
        authenticated=authenticated and configured,
        session_expires_at=expires_at if authenticated else None,
    )


@router.post(
    "/setup",
    response_model=AuthenticatedSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def setup_owner(
    payload: OwnerSetupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthenticatedSessionResponse:
    settings = _settings(request)
    if settings.auth_mode != "password":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Protected mode is disabled.",
        )
    _require_public_origin(request, settings)
    if owner_exists(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner setup is already complete.",
        )

    try:
        check_authentication_allowed(db)
        complete_owner_setup(
            db,
            setup_token=payload.setup_token,
            password=payload.password,
            display_name=payload.display_name,
        )
    except AuthenticationLocked as exc:
        raise _locked_error(exc) from exc
    except PasswordValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except OwnerAlreadyConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner setup is already complete.",
        ) from exc
    except ValueError as exc:
        try:
            record_login_failure(db)
        except AuthenticationLocked as locked:
            raise _locked_error(locked) from locked
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Setup could not be completed.",
        ) from exc

    record_login_success(db)
    issued = create_auth_session(db, remember_device=False)
    set_auth_cookies(response, issued, secure=settings.cookie_secure)
    return _session_response(issued)


@router.post("/login", response_model=AuthenticatedSessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthenticatedSessionResponse:
    settings = _settings(request)
    if settings.auth_mode != "password":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Protected mode is disabled.",
        )
    _require_public_origin(request, settings)
    if not owner_exists(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner setup is required.",
        )

    try:
        check_authentication_allowed(db)
    except AuthenticationLocked as exc:
        raise _locked_error(exc) from exc

    if not verify_owner_password(db, payload.password):
        try:
            record_login_failure(db)
        except AuthenticationLocked as exc:
            raise _locked_error(exc) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    record_login_success(db)
    issued = create_auth_session(
        db,
        remember_device=payload.remember_device,
    )
    set_auth_cookies(response, issued, secure=settings.cookie_secure)
    return _session_response(issued)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Session = Depends(get_db)) -> Response:
    settings = _settings(request)
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    revoke_session(db, session_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response, secure=settings.cookie_secure)
    return response


@router.post("/change-password", response_model=AuthenticatedSessionResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthenticatedSessionResponse:
    settings = _settings(request)
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        issued = change_owner_password(
            db,
            current_session_token=session_token,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except PasswordValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password could not be changed.",
        ) from exc

    set_auth_cookies(response, issued, secure=settings.cookie_secure)
    return _session_response(issued)


@router.get("/security", response_model=SecuritySummaryResponse)
def get_security_summary(
    request: Request,
    db: Session = Depends(get_db),
) -> SecuritySummaryResponse:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    try:
        summary = security_summary(db, session_token)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        ) from exc
    return SecuritySummaryResponse(other_sessions=summary.other_sessions)


@router.post(
    "/sessions/revoke-others",
    response_model=RevokeSessionsResponse,
)
def sign_out_other_devices(
    request: Request,
    db: Session = Depends(get_db),
) -> RevokeSessionsResponse:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    try:
        revoked = revoke_other_sessions(db, session_token)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        ) from exc
    return RevokeSessionsResponse(revoked_sessions=revoked)
