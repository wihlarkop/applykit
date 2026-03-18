from fastapi import APIRouter, Depends
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
    _provider_from_model,
    get_llm_config,
    get_provider_api_key,
    get_setting,
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
    active_provider = _provider_from_model(active_model)

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
                current_model=current_model,
            )
        )
    return IntegrationsResponse(integrations=integrations)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(req: UpdateSettingsRequest, db: Session = Depends(get_db)):
    # Migrate legacy global key to per-provider storage on first new-style save
    current_model = get_setting(db, "llm_provider") or ""
    current_provider = _provider_from_model(current_model)
    if current_provider and not get_provider_api_key(db, current_provider):
        legacy_key = get_setting(db, "llm_api_key") or ""
        if legacy_key:
            set_provider_api_key(db, current_provider, legacy_key)

    # Store key per provider instead of globally
    provider = _provider_from_model(req.model)
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
    # Migrate legacy global api key to per-provider storage before switching away.
    # Old system stored one key in "llm_api_key"; new system uses "api_key_{provider}".
    current_model = get_setting(db, "llm_provider") or ""
    current_provider = _provider_from_model(current_model)
    if current_provider and not get_provider_api_key(db, current_provider):
        legacy_key = get_setting(db, "llm_api_key") or ""
        if legacy_key:
            set_provider_api_key(db, current_provider, legacy_key)

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
