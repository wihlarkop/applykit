import pytest
from pydantic import ValidationError

from app.config import Settings


def test_auth_defaults_to_disabled_with_local_http_cookie() -> None:
    settings = Settings()

    assert settings.auth_mode == "disabled"
    assert settings.cookie_secure is False


def test_password_mode_and_secure_cookie_can_be_enabled_explicitly() -> None:
    settings = Settings(auth_mode="password", cookie_secure=True)

    assert settings.auth_mode == "password"
    assert settings.cookie_secure is True


def test_unknown_auth_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(auth_mode="proxy")
