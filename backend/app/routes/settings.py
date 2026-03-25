from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ActivateProviderRequest,
    IntegrationInfo,
    IntegrationsResponse,
    ModelOption,
    ModelsResponse,
    ProviderInfo,
    SettingsResponse,
    TestConnectionResponse,
    UpdateSettingsRequest,
)
from app.services.settings import (
    KNOWN_MODELS,
    clear_provider_api_key,
    get_llm_config,
    get_provider_api_key,
    get_setting,
    migrate_legacy_api_key,
    provider_from_model,
    set_active_model,
    set_provider_api_key,
    set_setting,
)

router = APIRouter()

PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "anthropic": "Anthropic Claude",
    "openai": "OpenAI",
    "ollama": "Ollama (local)",
}


def _mask_api_key(key: str) -> str | None:
    """Return a masked version of an API key for display."""
    if not key:
        return None
    if len(key) <= 8:
        return "•" * len(key)
    return key[:4] + "•" * (len(key) - 8) + key[-4:]


@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    db_model = get_setting(db, "llm_provider")
    model, api_key = get_llm_config(db)
    source = "database" if db_model and api_key else "none"
    return SettingsResponse(
        model=model or None,
        api_key_configured=bool(api_key),
        source=source,
    )


@router.get("/settings/integrations", response_model=IntegrationsResponse)
def get_integrations(db: Session = Depends(get_db)):
    active_model = get_setting(db, "llm_provider") or ""
    active_provider = provider_from_model(active_model)

    integrations = []
    for provider_id, models in KNOWN_MODELS.items():
        api_key = get_provider_api_key(db, provider_id) or ""
        # Legacy fallback for the active provider
        if not api_key and provider_id == active_provider:
            api_key = get_setting(db, "llm_api_key") or ""

        is_active = provider_id == active_provider
        current_model = (
            active_model
            if is_active
            else get_setting(db, f"selected_model_{provider_id}")
        )

        integrations.append(
            IntegrationInfo(
                id=provider_id,
                label=PROVIDER_LABELS.get(provider_id, provider_id),
                is_active=is_active,
                api_key_configured=bool(api_key),
                masked_api_key=_mask_api_key(api_key) if api_key else None,
                api_key=api_key if api_key else None,
                current_model=current_model,
            )
        )
    return IntegrationsResponse(integrations=integrations)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(req: UpdateSettingsRequest, db: Session = Depends(get_db)):
    migrate_legacy_api_key(db)

    # Store key per provider instead of globally
    provider = provider_from_model(req.model)
    if provider:
        set_provider_api_key(db, provider, req.api_key)
        set_setting(db, f"selected_model_{provider}", req.model)
    else:
        set_setting(db, "llm_api_key", req.api_key)
    if req.activate:
        set_active_model(db, req.model)
    model, api_key = get_llm_config(db)
    return SettingsResponse(
        model=model or None,
        api_key_configured=bool(api_key),
        source="database",
    )


@router.put("/settings/activate")
def activate_provider(req: ActivateProviderRequest, db: Session = Depends(get_db)):
    """Switch active provider without changing any stored API key."""
    migrate_legacy_api_key(db)

    provider_id = req.provider_id
    # Use the last selected model for this provider, or the first available
    saved_model = get_setting(db, f"selected_model_{provider_id}")
    if not saved_model:
        models = KNOWN_MODELS.get(provider_id, [])
        saved_model = models[0] if models else provider_id
    set_active_model(db, saved_model)
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


@router.delete("/settings/integrations/{provider_id}", response_model=IntegrationsResponse)
def disconnect_provider(provider_id: str, db: Session = Depends(get_db)):
    """Remove the stored API key for a provider. If it was active, clear the active model."""
    if provider_id not in KNOWN_MODELS:
        raise HTTPException(status_code=404, detail="Unknown provider")

    clear_provider_api_key(db, provider_id)

    # If the disconnected provider was active, clear the active model
    active_model = get_setting(db, "llm_provider") or ""
    active_provider = provider_from_model(active_model)
    if active_provider == provider_id:
        set_setting(db, "llm_provider", "")

    return get_integrations(db)


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
