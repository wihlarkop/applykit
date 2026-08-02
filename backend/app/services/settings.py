from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.llm.catalog import (
    CATALOG,
    get_provider_models,
    provider_from_model,
    provider_requires_api_key,
)
from app.models import AppSetting
from app.services.provider_credential_vault import (
    clear_provider_credentials,
    decrypt_provider_credential,
    get_active_provider_credential,
    migrate_legacy_provider_credentials,
    upsert_active_provider_credential,
)

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

# Backward-compatible projection for callers that still need provider -> model IDs.
KNOWN_MODELS: dict[str, list[str]] = {
    provider.id: list(get_provider_models(provider.id))
    for provider in CATALOG.providers
}


def is_llm_configured(model: str, api_key: str | None) -> bool:
    """Return whether the selected model has everything needed to make a call."""
    if not model:
        return False
    provider_id = provider_from_model(model)
    if not provider_requires_api_key(provider_id):
        return True
    return bool(api_key)


def get_setting(db: Session, key: str) -> str | None:
    row = db.query(AppSetting).filter_by(key=key).first()
    return row.value if row else None


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(AppSetting).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


def normalize_provider_base_url(provider_id: str, value: str | None) -> str | None:
    """Validate and normalize the optional endpoint supported by a provider."""
    if provider_id != "ollama":
        return None

    normalized = (value or DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
    if not normalized:
        normalized = DEFAULT_OLLAMA_BASE_URL

    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Ollama Base URL must start with http:// or https://.")
    if not parsed.hostname:
        raise ValueError("Ollama Base URL must include a valid host.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Ollama Base URL must not contain embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("Ollama Base URL must not include a query string or fragment.")
    return normalized


def get_provider_base_url(db: Session, provider_id: str | None) -> str | None:
    if provider_id != "ollama":
        return None
    stored = get_setting(db, "base_url_ollama")
    return normalize_provider_base_url("ollama", stored)


def set_provider_base_url(db: Session, provider_id: str, value: str | None) -> str | None:
    normalized = normalize_provider_base_url(provider_id, value)
    if normalized is not None:
        set_setting(db, f"base_url_{provider_id}", normalized)
    return normalized


def clear_provider_base_url(db: Session, provider_id: str) -> None:
    if provider_id == "ollama":
        set_setting(db, f"base_url_{provider_id}", "")


def get_provider_api_key(db: Session, provider_id: str) -> str | None:
    """Return the decrypted manually active credential for a provider."""
    migrate_legacy_provider_credentials(db)
    credential = get_active_provider_credential(db, provider_id)
    if not credential:
        return None
    return decrypt_provider_credential(credential)


def set_provider_api_key(db: Session, provider_id: str, api_key: str) -> None:
    """Create or replace the manually active credential for a provider."""
    migrate_legacy_provider_credentials(db)
    upsert_active_provider_credential(db, provider_id, api_key)
    # Clear any plaintext remnants left by older ApplyKit versions.
    set_setting(db, f"api_key_{provider_id}", "")


def clear_provider_api_key(db: Session, provider_id: str) -> None:
    """Remove every stored credential for a provider."""
    clear_provider_credentials(db, provider_id)
    set_setting(db, f"api_key_{provider_id}", "")


def set_active_model(db: Session, model: str) -> None:
    """Set the single active model. Only one model can be active at a time."""
    set_setting(db, "llm_provider", model)


def get_llm_config(db: Session) -> tuple[str, str]:
    """Return (model_string, active_api_key) for the active provider."""
    model = get_setting(db, "llm_provider") or ""
    if not model:
        return "", ""

    provider_id = provider_from_model(model)
    if not provider_requires_api_key(provider_id):
        return model, ""

    migrate_legacy_provider_credentials(db)
    if not provider_id:
        return model, ""

    credential = get_active_provider_credential(db, provider_id)
    if not credential:
        return model, ""
    return model, decrypt_provider_credential(credential)


def migrate_legacy_api_key(db: Session) -> None:
    """Backward-compatible alias for the encrypted credential migration."""
    migrate_legacy_provider_credentials(db)
