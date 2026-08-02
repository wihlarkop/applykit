"""Centralized application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./applykit.db"

    # Credential vault
    # Supply a Fernet key through CREDENTIAL_ENCRYPTION_KEY in managed
    # deployments. Local installs automatically create the fallback key file.
    credential_encryption_key: str | None = None
    credential_key_file: str = ".applykit/credential.key"
    max_provider_credentials: int = 20

    # Community authentication
    # disabled: local-first mode without login (default)
    # password: optional single-owner protected mode
    auth_mode: Literal["disabled", "password"] = "disabled"
    cookie_secure: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # App
    app_title: str = "ApplyKit API"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
