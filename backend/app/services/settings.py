import os

from sqlalchemy.orm import Session

from app.models import AppSetting

# Full LiteLLM model strings, grouped by provider family.
# Used by GET /api/settings/models and the Settings UI.
KNOWN_MODELS: dict[str, list[str]] = {
    "gemini": [
        "gemini/gemini-3.1-pro-preview",
        "gemini/gemini-3-flash-preview",
        "gemini/gemini-3.1-flash-lite-preview",
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash-lite",
    ],
    "anthropic": [
        "anthropic/claude-haiku-4-5-20251001",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-opus-4-6",
    ],
    "openai": [
        "openai/gpt-5.4-pro-2026-03-05",
        "openai/gpt-5.4-2026-03-05",
        "openai/gpt-5.2-2025-12-11",
        "openai/gpt-5.2-pro-2025-12-11",
        "openai/gpt-5.1-2025-11-13",
        "openai/gpt-5-mini-2025-08-07",
        "openai/gpt-5-nano-2025-08-07",
        "openai/gpt-5-pro-2025-10-06",
        "openai/gpt-5-2025-08-07",
        "openai/gpt-4.1-2025-04-14",
        "openai/gpt-4.1-mini-2025-04-14",
        "openai/gpt-4.1-nano-2025-04-14",
        "openai/gpt-4o-2024-08-06",
        "openai/gpt-4o-mini-2024-07-18",
        "openai/gpt-4-turbo-2024-04-09",
        "openai/gpt-4-0613",
        "openai/gpt-3.5-turbo-0125",
        "openai/o1-2024-12-17",
        "openai/o1-pro-2025-03-19",
        "openai/o4-mini-2025-04-16",
        "openai/o3-2025-04-16",
        "openai/openai/o3-mini-2025-01-31",
        "openai/o3-pro-2025-06-10",
    ],
    "ollama": [
        "ollama/llama3.2",
        "ollama/llama3.1",
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
