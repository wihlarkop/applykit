from sqlalchemy.orm import Session

from app.models import AppSetting

# Full LiteLLM model strings, grouped by provider family.
# Used by GET /api/settings/models and the Settings UI.
KNOWN_MODELS: dict[str, list[str]] = {
    "gemini": [
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash-lite",
        "gemini/gemini-3.1-flash-lite-preview",
        "gemini/gemini-3-flash-preview",
        "gemini/gemini-3.1-pro-preview",
    ],
    "anthropic": [
        "anthropic/claude-haiku-4-5-20251001",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-opus-4-6",
    ],
    "openai": [
        "openai/gpt-4o-mini-2024-07-18",
        "openai/gpt-4o-2024-08-06",
        "openai/gpt-4.1-2025-04-14",
        "openai/gpt-4.1-mini-2025-04-14",
        "openai/o4-mini-2025-04-16",
        "openai/o3-2025-04-16",
    ],
    "ollama": [
        "ollama/llama4",
        "ollama/llama3.2",
        "ollama/llama3.1",
        "ollama/llama3",
        "ollama/qwen3.5",
        "ollama/qwen3-next",
        "ollama/glm-5",
        "ollama/glm-4.7-flash",
    ],
}

KEYLESS_PROVIDERS = frozenset({"ollama"})


def provider_from_model(model: str) -> str | None:
    """Extract provider id from a LiteLLM model string like 'gemini/gemini-2.5-flash'."""
    if not model:
        return None
    for provider_id in KNOWN_MODELS:
        if model.startswith(provider_id + "/") or model == provider_id:
            return provider_id
    return None


def provider_requires_api_key(provider_id: str | None) -> bool:
    """Return whether a provider requires a stored secret to be usable."""
    return provider_id not in KEYLESS_PROVIDERS


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
