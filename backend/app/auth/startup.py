"""Startup initialization for optional protected mode."""

import logging

from sqlalchemy import select

from app.auth.service import issue_setup_token, owner_exists, record_security_event
from app.config import Settings
from app.database import SessionLocal
from app.models import AuthSetupToken

logger = logging.getLogger(__name__)


def initialize_auth(settings: Settings) -> None:
    """Record auth mode and issue a one-time setup token when required."""
    logger.info("ApplyKit authentication mode: %s", settings.auth_mode)
    if settings.auth_mode == "password" and not settings.cookie_secure:
        logger.warning(
            "Protected mode is using COOKIE_SECURE=false. "
            "Use HTTPS and COOKIE_SECURE=true for remote deployments."
        )

    with SessionLocal() as db:
        record_security_event(db, f"auth_mode_{settings.auth_mode}_started")
        db.commit()

        if settings.auth_mode != "password" or owner_exists(db):
            return

        # A fresh token is generated on every unclaimed startup. This ensures
        # that only the token visible in the latest server logs can be used.
        db.query(AuthSetupToken).delete()
        db.commit()
        setup_token = issue_setup_token(db)
        logger.warning(
            "ApplyKit protected mode requires owner setup. "
            "Open the setup page and enter this one-time token within 30 minutes: %s",
            setup_token,
        )
