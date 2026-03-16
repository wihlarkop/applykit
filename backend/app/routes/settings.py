from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ModelOption,
    ModelsResponse,
    ProviderInfo,
    SettingsResponse,
    TestConnectionResponse,
    UpdateSettingsRequest,
)
from app.services.settings import (
    KNOWN_MODELS,
    get_llm_config,
    get_setting,
    set_setting,
)

router = APIRouter()

PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "anthropic": "Anthropic Claude",
    "openai": "OpenAI",
    "ollama": "Ollama (local)",
}


def _detect_source(db_model: str | None, db_api_key: str | None) -> str:
    """Determine whether the active config comes from the DB or nowhere."""
    if db_model and db_api_key:
        return "database"
    return "none"


@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    db_model = get_setting(db, "llm_provider")
    db_api_key = get_setting(db, "llm_api_key")
    model, api_key = get_llm_config(db)
    return SettingsResponse(
        model=model or None,
        api_key_configured=bool(api_key),
        source=_detect_source(db_model, db_api_key),
    )


@router.put("/settings", response_model=SettingsResponse)
def update_settings(req: UpdateSettingsRequest, db: Session = Depends(get_db)):
    set_setting(db, "llm_provider", req.model)
    set_setting(db, "llm_api_key", req.api_key)
    model, api_key = get_llm_config(db)
    return SettingsResponse(
        model=model or None,
        api_key_configured=bool(api_key),
        source="database",
    )


@router.post("/settings/test", response_model=TestConnectionResponse)
def test_connection(req: UpdateSettingsRequest):
    import litellm

    try:
        response = litellm.completion(
            model=req.model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            api_key=req.api_key,
            timeout=15,
            max_tokens=5,
        )
        content = response.choices[0].message.content if response.choices else ""
        if content:
            return TestConnectionResponse(ok=True, message="Connection successful.")
        return TestConnectionResponse(ok=False, message="LLM returned empty response.")
    except Exception as e:
        return TestConnectionResponse(ok=False, message=str(e))


@router.get("/settings/models", response_model=ModelsResponse)
def get_models():
    return ModelsResponse(
        providers=[
            ProviderInfo(
                id=provider_id,
                label=PROVIDER_LABELS.get(provider_id, provider_id),
                models=[ModelOption(value=m, label=m) for m in models],
                requires_api_key=provider_id != "ollama",
            )
            for provider_id, models in KNOWN_MODELS.items()
        ]
    )
