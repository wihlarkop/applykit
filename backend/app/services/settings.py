import os

from sqlalchemy.orm import Session

from app.models import AppSetting

# Full LiteLLM model strings, grouped by provider family.
# Used by GET /api/settings/models and the Settings UI.
KNOWN_MODELS: dict[str, list[str]] = {
    "gemini": [
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash-lite",
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-pro",
    ],
    "anthropic": [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
    ],
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "o1-mini",
        "o1",
        "o3-mini",
    ],
    "ollama": [
        "ollama/llama3.2",
        "ollama/llama3.1",
        "ollama/mistral",
    ],
}


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


def get_llm_config(db: Session) -> tuple[str, str]:
    """Return (model_string, api_key). DB takes precedence over env vars."""
    model = get_setting(db, "llm_provider") or os.getenv("LLM_PROVIDER", "").strip()
    api_key = get_setting(db, "llm_api_key") or os.getenv("LLM_API_KEY", "").strip()
    return model, api_key
