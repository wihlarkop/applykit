from sqlalchemy.orm import Session

from app.llm.catalog import (
    CATALOG,
    get_provider_models,
    provider_from_model,
    provider_requires_api_key,
)
from app.models import AppSetting

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


def get_provider_api_key(db: Session, provider_id: str) -> str | None:
    """Get the stored API key for a specific provider."""
    return get_setting(db, f"api_key_{provider_id}")


def set_provider_api_key(db: Session, provider_id: str, api_key: str) -> None:
    """Store API key for a specific provider."""
    set_setting(db, f"api_key_{provider_id}", api_key)


def clear_provider_api_key(db: Session, provider_id: str) -> None:
    """Remove the stored API key for a provider."""
    set_setting(db, f"api_key_{provider_id}", "")


def set_active_model(db: Session, model: str) -> None:
    """Set the single active model. Only one model can be active at a time."""
    set_setting(db, "llm_provider", model)


def get_llm_config(db: Session) -> tuple[str, str]:
    """Return (model_string, api_key) for the currently active provider."""
    model = get_setting(db, "llm_provider") or ""
    if not model:
        return "", ""

    provider_id = provider_from_model(model)
    if not provider_requires_api_key(provider_id):
        return model, ""

    if provider_id:
        api_key = get_provider_api_key(db, provider_id) or ""
        # Legacy fallback: old single-key setup
        if not api_key:
            api_key = get_setting(db, "llm_api_key") or ""
    else:
        api_key = get_setting(db, "llm_api_key") or ""
    return model, api_key


def migrate_legacy_api_key(db: Session) -> None:
    """Migrate the old global llm_api_key to per-provider storage if needed."""
    current_model = get_setting(db, "llm_provider") or ""
    current_provider = provider_from_model(current_model)
    if not current_provider or not provider_requires_api_key(current_provider):
        return
    if not get_provider_api_key(db, current_provider):
        legacy_key = get_setting(db, "llm_api_key") or ""
        if legacy_key:
            set_provider_api_key(db, current_provider, legacy_key)
