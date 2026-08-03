import pytest
from cryptography.fernet import Fernet

from app.config import Settings
from app.security.deployment import (
    DeploymentSecurityError,
    is_loopback_origin,
    manual_bind_host,
    validate_deployment_security,
)


def test_loopback_origin_accepts_localhost_ipv4_and_ipv6() -> None:
    assert is_loopback_origin("http://localhost:5173")
    assert is_loopback_origin("https://127.0.0.1:3000")
    assert is_loopback_origin("http://127.42.0.8")
    assert is_loopback_origin("http://[::1]:5173")


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://192.168.1.10:5173",
        "https://applykit.example.com",
        "ftp://localhost",
        "http://user:pass@localhost:5173",
        "http://localhost:5173/path",
        "http://localhost:5173?debug=1",
    ],
)
def test_loopback_origin_rejects_non_origin_or_non_loopback_values(
    origin: str,
) -> None:
    assert not is_loopback_origin(origin)


def test_local_mode_allows_default_loopback_configuration() -> None:
    settings = Settings(
        deployment_mode="local",
        auth_mode="disabled",
        cookie_secure=False,
        debug=False,
        cors_origins=["http://localhost:5173"],
    )
    validate_deployment_security(settings)
    assert manual_bind_host(settings) == "127.0.0.1"


def test_local_mode_rejects_lan_or_public_origin() -> None:
    settings = Settings(
        deployment_mode="local",
        cors_origins=["http://192.168.1.20:5173"],
    )
    with pytest.raises(DeploymentSecurityError) as exc_info:
        validate_deployment_security(settings)
    assert "DEPLOYMENT_MODE=remote" in str(exc_info.value)


def test_remote_mode_reports_all_unsafe_settings_together() -> None:
    settings = Settings(
        deployment_mode="remote",
        auth_mode="disabled",
        cookie_secure=False,
        debug=True,
        cors_origins=["*", "http://applykit.example.com"],
        credential_encryption_key=None,
        credential_encryption_key_file=None,
    )
    with pytest.raises(DeploymentSecurityError) as exc_info:
        validate_deployment_security(settings)

    message = str(exc_info.value)
    assert 'AUTH_MODE must be "password"' in message
    assert "COOKIE_SECURE must be true" in message
    assert "DEBUG must be false" in message
    assert "wildcard CORS" in message
    assert "must use HTTPS" in message
    assert "external credential encryption key" in message


def test_remote_mode_accepts_hardened_configuration() -> None:
    settings = Settings(
        deployment_mode="remote",
        auth_mode="password",
        cookie_secure=True,
        debug=False,
        cors_origins=["https://applykit.example.com"],
        credential_encryption_key=Fernet.generate_key().decode(),
    )
    validate_deployment_security(settings)
    assert manual_bind_host(settings) == "0.0.0.0"
