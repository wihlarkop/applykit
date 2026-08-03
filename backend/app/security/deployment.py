"""Fail-closed deployment security validation."""

from __future__ import annotations

from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

from app.config import Settings
from app.security.secrets import reveal_secret


class DeploymentSecurityError(RuntimeError):
    """Raised when deployment settings would expose ApplyKit unsafely."""


def _is_exact_origin(origin: str, *, require_https: bool) -> bool:
    if not origin or origin == "*":
        return False

    parsed = urlsplit(origin)
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    if parsed.scheme not in allowed_schemes:
        return False
    if not parsed.hostname:
        return False
    if parsed.username is not None or parsed.password is not None:
        return False
    if parsed.path not in {"", "/"}:
        return False
    if parsed.query or parsed.fragment:
        return False
    return True


def is_loopback_origin(origin: str) -> bool:
    """Return whether *origin* is an exact HTTP(S) loopback origin."""
    if not _is_exact_origin(origin, require_https=False):
        return False

    hostname = urlsplit(origin).hostname
    if hostname == "localhost":
        return True
    try:
        return ip_address(hostname or "").is_loopback
    except ValueError:
        return False


def _sqlite_database_parent(database_url: str) -> Path | None:
    try:
        url = make_url(database_url)
    except Exception:
        return None
    if not url.drivername.startswith("sqlite"):
        return None
    if not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser().resolve().parent


def validate_deployment_security(settings: Settings) -> None:
    """Reject unsafe local or remote deployment combinations."""
    violations: list[str] = []

    has_direct_key = bool(reveal_secret(settings.credential_encryption_key).strip())
    has_external_key_file = bool(settings.credential_encryption_key_file)
    if has_direct_key and has_external_key_file:
        violations.append(
            "Configure only one of CREDENTIAL_ENCRYPTION_KEY or "
            "CREDENTIAL_ENCRYPTION_KEY_FILE."
        )

    if settings.deployment_mode == "local":
        for origin in settings.cors_origins:
            if not is_loopback_origin(origin):
                violations.append(
                    f'Local mode CORS origin "{origin}" is not loopback; '
                    "use DEPLOYMENT_MODE=remote for network access."
                )
    else:
        if settings.auth_mode != "password":
            violations.append('AUTH_MODE must be "password".')
        if not settings.cookie_secure:
            violations.append("COOKIE_SECURE must be true.")
        if settings.debug:
            violations.append("DEBUG must be false.")
        if "*" in settings.cors_origins:
            violations.append("Remote mode must not use wildcard CORS.")

        for origin in settings.cors_origins:
            if origin == "*":
                continue
            if not _is_exact_origin(origin, require_https=True):
                violations.append(
                    f'Remote CORS origin "{origin}" must use HTTPS and be an '
                    "exact origin without credentials, paths, queries, or fragments."
                )

        if not (has_direct_key or has_external_key_file):
            violations.append(
                "Remote mode requires an external credential encryption key."
            )

        if settings.credential_encryption_key_file:
            database_parent = _sqlite_database_parent(settings.database_url)
            key_parent = (
                Path(settings.credential_encryption_key_file)
                .expanduser()
                .resolve()
                .parent
            )
            if database_parent is not None and database_parent == key_parent:
                violations.append(
                    "Remote SQLite deployments must keep the credential key file "
                    "in a separate storage location from the database."
                )

    if violations:
        details = "\n".join(f"- {violation}" for violation in violations)
        raise DeploymentSecurityError(
            f"Unsafe {settings.deployment_mode} deployment configuration:\n{details}"
        )


def manual_bind_host(settings: Settings) -> str:
    """Return the safe host used by the manual development runner."""
    return "127.0.0.1" if settings.deployment_mode == "local" else "0.0.0.0"
