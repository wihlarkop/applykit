import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import ProviderNotFoundError
from app.llm.catalog import CATALOG, get_provider
from app.llm.schemas import ModelOption, ModelsResponse, ProviderInfo
from app.public_errors import PROVIDER_CONNECTION_ERROR_MESSAGE
from app.schemas import (
    ActivateProviderRequest,
    IntegrationInfo,
    IntegrationsResponse,
    SettingsResponse,
    TestConnectionResponse,
    UpdateSettingsRequest,
)
from app.services.settings import (
    clear_provider_api_key,
    get_llm_config,
    get_provider_api_key,
    get_setting,
    is_llm_configured,
    migrate_legacy_api_key,
    provider_from_model,
    provider_requires_api_key,
    set_active_model,
    set_provider_api_key,
    set_setting,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _mask_api_key(key: str) -> str | None:
    """Return a masked version of an API key for display."""
    if not key:
        return None
    if len(key) <= 8:
        return "•" * len(key)
    return key[:4] + "•" * (len(key) - 8) + key[-4:]


@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    db_model = get_setting(db, "llm_provider") or ""
    model, api_key = get_llm_config(db)
    configured = is_llm_configured(model, api_key)
    source = "database" if db_model and configured else "none"
    return SettingsResponse(
        model=model or None,
        api_key_configured=configured,
        source=source,
    )


@router.get("/settings/integrations", response_model=IntegrationsResponse)
def get_integrations(db: Session = Depends(get_db)):
    active_model = get_setting(db, "llm_provider") or ""
    active_provider = provider_from_model(active_model)

    integrations = []
    for provider in CATALOG.providers:
        api_key = ""
        if provider_requires_api_key(provider.id):
            api_key = get_provider_api_key(db, provider.id) or ""
            # Legacy fallback for the active provider
            if not api_key and provider.id == active_provider:
                api_key = get_setting(db, "llm_api_key") or ""

        is_active = provider.id == active_provider
        current_model = (
            active_model
            if is_active
            else get_setting(db, f"selected_model_{provider.id}")
        )

        integrations.append(
            IntegrationInfo(
                id=provider.id,
                label=provider.label,
                is_active=is_active,
                api_key_configured=bool(api_key),
                masked_api_key=_mask_api_key(api_key) if api_key else None,
                current_model=current_model,
            )
        )
    return IntegrationsResponse(integrations=integrations)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(req: UpdateSettingsRequest, db: Session = Depends(get_db)):
    migrate_legacy_api_key(db)

    # An omitted or blank key means "keep the existing secret". Providers that do
    # not require a key never persist placeholders or submitted secret values.
    provider_id = provider_from_model(req.model)
    api_key = req.api_key.strip() if req.api_key else ""
    if provider_id:
        if provider_requires_api_key(provider_id):
            if api_key:
                set_provider_api_key(db, provider_id, api_key)
        else:
            clear_provider_api_key(db, provider_id)
        set_setting(db, f"selected_model_{provider_id}", req.model)
    elif api_key:
        set_setting(db, "llm_api_key", api_key)

    if req.activate:
        set_active_model(db, req.model)

    model, configured_api_key = get_llm_config(db)
    return SettingsResponse(
        model=model or None,
        api_key_configured=is_llm_configured(model, configured_api_key),
        source="database",
    )


@router.put("/settings/activate")
def activate_provider(req: ActivateProviderRequest, db: Session = Depends(get_db)):
    """Switch active provider without changing any stored API key."""
    migrate_legacy_api_key(db)

    provider = get_provider(req.provider_id)
    if provider is None:
        raise ProviderNotFoundError(req.provider_id)

    saved_model = get_setting(db, f"selected_model_{provider.id}")
    if not saved_model:
        saved_model = provider.models[0].id
    set_active_model(db, saved_model)
    model, api_key = get_llm_config(db)
    return SettingsResponse(
        model=model or None,
        api_key_configured=is_llm_configured(model, api_key),
        source="database",
    )


@router.post("/settings/test", response_model=TestConnectionResponse)
def test_connection(req: UpdateSettingsRequest):
    import litellm

    provider_id = provider_from_model(req.model)
    api_key = req.api_key.strip() if req.api_key else ""
    if provider_requires_api_key(provider_id) and not api_key:
        return TestConnectionResponse(
            ok=False,
            message="API key is required for this provider.",
        )

    request_kwargs = {
        "model": req.model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "timeout": 15,
        "max_tokens": 5,
    }
    if api_key:
        request_kwargs["api_key"] = api_key

    try:
        response = litellm.completion(**request_kwargs)
        content = response.choices[0].message.content if response.choices else ""
        if content:
            return TestConnectionResponse(ok=True, message="Connection successful.")
        return TestConnectionResponse(ok=False, message="LLM returned empty response.")
    except Exception as exc:
        logger.warning(
            "LLM connection test failed for model %s",
            req.model,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return TestConnectionResponse(
            ok=False,
            message=PROVIDER_CONNECTION_ERROR_MESSAGE,
        )


@router.delete("/settings/integrations/{provider_id}", response_model=IntegrationsResponse)
def disconnect_provider(provider_id: str, db: Session = Depends(get_db)):
    """Remove the stored API key for a provider. If it was active, clear the active model."""
    if get_provider(provider_id) is None:
        raise ProviderNotFoundError(provider_id)

    clear_provider_api_key(db, provider_id)

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
                id=provider.id,
                label=provider.label,
                auth_type=provider.auth_type.value,
                local=provider.local,
                requires_api_key=provider_requires_api_key(provider.id),
                models=[
                    ModelOption(
                        value=model.id,
                        label=model.label,
                        status=model.status.value,
                        capabilities=sorted(capability.value for capability in model.capabilities),
                        traits=sorted(trait.value for trait in model.traits),
                        free_tier=model.free_tier,
                    )
                    for model in provider.models
                ],
            )
            for provider in CATALOG.providers
        ]
    )
