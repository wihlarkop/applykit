from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings as get_app_settings
from app.credential_schemas import (
    CreateProviderCredentialRequest,
    CredentialIntegrationInfo,
    CredentialIntegrationsResponse,
    CredentialPolicyResponse,
    ProviderCredentialInfo,
    ProviderCredentialsResponse,
    ProviderSettingsRequest,
    UpdateCredentialPolicyRequest,
    UpdateProviderCredentialRequest,
)
from app.database import get_db
from app.exceptions import ProviderNotFoundError, ValidationAppError
from app.llm.catalog import CATALOG, get_provider
from app.llm.model_selection import supports_custom_models, validate_model_id
from app.llm.provider_credentials import credential_url_for_provider
from app.llm.schemas import ModelOption, ModelsResponse, ProviderInfo
from app.schemas import (
    ActivateProviderRequest,
    SettingsResponse,
    TestConnectionResponse,
)
from app.services.provider_connection import test_provider_connection
from app.services.provider_credential_rotation import (
    CredentialStrategy,
    get_credential_policy,
    update_credential_policy,
)
from app.services.provider_credential_vault import (
    CredentialVaultError,
    activate_provider_credential,
    create_provider_credential,
    decrypt_provider_credential,
    delete_provider_credential,
    get_provider_credential,
    list_provider_credentials,
    migrate_legacy_provider_credentials,
    rename_provider_credential,
    replace_provider_credential_secret,
)
from app.services.settings import (
    clear_provider_api_key,
    clear_provider_base_url,
    get_llm_config,
    get_provider_api_key,
    get_provider_base_url,
    get_setting,
    is_llm_configured,
    migrate_legacy_api_key,
    normalize_provider_base_url,
    provider_from_model,
    provider_requires_api_key,
    set_active_model,
    set_provider_api_key,
    set_provider_base_url,
    set_setting,
)

router = APIRouter()


def _validate_model_or_422(model_id: str) -> str:
    try:
        return validate_model_id(model_id)
    except ValueError as exc:
        raise ValidationAppError(str(exc)) from exc


def _normalize_base_url_or_422(provider_id: str | None, value: str | None) -> str | None:
    if not provider_id:
        return None
    try:
        return normalize_provider_base_url(provider_id, value)
    except ValueError as exc:
        raise ValidationAppError(str(exc)) from exc


def _provider_or_404(provider_id: str):
    provider = get_provider(provider_id)
    if provider is None:
        raise ProviderNotFoundError(provider_id)
    return provider


def _credential_or_422(provider_id: str, credential_id: int, db: Session):
    credential = get_provider_credential(db, provider_id, credential_id)
    if credential is None:
        raise ValidationAppError("Credential was not found.")
    return credential


def _credential_info(credential) -> ProviderCredentialInfo:
    return ProviderCredentialInfo.model_validate(credential)


def _credential_list_response(
    provider_id: str,
    db: Session,
) -> ProviderCredentialsResponse:
    settings = get_app_settings()
    return ProviderCredentialsResponse(
        provider_id=provider_id,
        credentials=[
            _credential_info(item)
            for item in list_provider_credentials(db, provider_id)
        ],
        max_credentials=settings.max_provider_credentials,
    )


def _credential_strategy(db: Session, provider_id: str) -> str:
    return get_credential_policy(db, provider_id).strategy


def _policy_response(provider_id: str, db: Session) -> CredentialPolicyResponse:
    policy = get_credential_policy(db, provider_id)
    return CredentialPolicyResponse(
        provider_id=provider_id,
        strategy=policy.strategy,
        max_attempts=policy.max_attempts,
    )


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


@router.get(
    "/settings/integrations",
    response_model=CredentialIntegrationsResponse,
)
def get_integrations(db: Session = Depends(get_db)):
    migrate_legacy_provider_credentials(db)
    active_model = get_setting(db, "llm_provider") or ""
    active_provider = provider_from_model(active_model)

    integrations = []
    for provider in CATALOG.providers:
        credentials = (
            list_provider_credentials(db, provider.id)
            if provider_requires_api_key(provider.id)
            else []
        )
        active_credential = next(
            (
                credential
                for credential in credentials
                if credential.is_active and credential.is_enabled
            ),
            None,
        )
        is_active = provider.id == active_provider
        current_model = (
            active_model
            if is_active
            else get_setting(db, f"selected_model_{provider.id}")
        ) or None

        integrations.append(
            CredentialIntegrationInfo(
                id=provider.id,
                label=provider.label,
                is_active=is_active,
                api_key_configured=bool(active_credential),
                masked_api_key=(
                    active_credential.masked_secret if active_credential else None
                ),
                current_model=current_model,
                base_url=get_provider_base_url(db, provider.id),
                credential_count=len(credentials),
                active_credential_id=(
                    active_credential.id if active_credential else None
                ),
                active_credential_label=(
                    active_credential.label if active_credential else None
                ),
                credential_strategy=(
                    _credential_strategy(db, provider.id)
                    if provider_requires_api_key(provider.id)
                    else CredentialStrategy.MANUAL.value
                ),
            )
        )
    return CredentialIntegrationsResponse(integrations=integrations)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(req: ProviderSettingsRequest, db: Session = Depends(get_db)):
    migrate_legacy_api_key(db)

    model_id = _validate_model_or_422(req.model)
    provider_id = provider_from_model(model_id)
    api_key = req.api_key.strip() if req.api_key else ""
    if provider_id:
        if provider_requires_api_key(provider_id):
            if api_key:
                set_provider_api_key(db, provider_id, api_key)
        else:
            clear_provider_api_key(db, provider_id)
        if provider_id == "ollama":
            base_url = _normalize_base_url_or_422(
                provider_id,
                getattr(req, "base_url", None),
            )
            set_provider_base_url(db, provider_id, base_url)
        set_setting(db, f"selected_model_{provider_id}", model_id)

    if req.activate:
        set_active_model(db, model_id)

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

    provider = _provider_or_404(req.provider_id)
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
def test_connection(req: ProviderSettingsRequest):
    model_id = _validate_model_or_422(req.model)
    provider_id = provider_from_model(model_id)
    api_key = req.api_key.strip() if req.api_key else ""
    if provider_requires_api_key(provider_id) and not api_key:
        return TestConnectionResponse(
            ok=False,
            message="API key is required for this provider.",
        )

    api_base = _normalize_base_url_or_422(
        provider_id,
        getattr(req, "base_url", None),
    )
    return test_provider_connection(
        model_id,
        api_key or None,
        api_base=api_base,
    )


@router.post(
    "/settings/integrations/{provider_id}/test",
    response_model=TestConnectionResponse,
)
def test_configured_integration(
    provider_id: str,
    db: Session = Depends(get_db),
):
    provider = _provider_or_404(provider_id)

    active_model = get_setting(db, "llm_provider") or ""
    active_provider = provider_from_model(active_model)
    saved_model = (
        active_model
        if active_provider == provider_id
        else get_setting(db, f"selected_model_{provider_id}")
    )
    model_id = saved_model or provider.models[0].id

    api_key = ""
    if provider_requires_api_key(provider_id):
        api_key = get_provider_api_key(db, provider_id) or ""
        if not api_key:
            return TestConnectionResponse(
                ok=False,
                message="Credential is not configured.",
            )

    return test_provider_connection(
        model_id,
        api_key or None,
        api_base=get_provider_base_url(db, provider_id),
        failure_message="Provider connection failed.",
    )


@router.get(
    "/settings/integrations/{provider_id}/credential-policy",
    response_model=CredentialPolicyResponse,
)
def get_credential_policy_route(
    provider_id: str,
    db: Session = Depends(get_db),
):
    _provider_or_404(provider_id)
    if not provider_requires_api_key(provider_id):
        raise ValidationAppError("This provider does not use API credentials.")
    return _policy_response(provider_id, db)


@router.put(
    "/settings/integrations/{provider_id}/credential-policy",
    response_model=CredentialPolicyResponse,
)
def update_credential_policy_route(
    provider_id: str,
    req: UpdateCredentialPolicyRequest,
    db: Session = Depends(get_db),
):
    _provider_or_404(provider_id)
    if not provider_requires_api_key(provider_id):
        raise ValidationAppError("This provider does not use API credentials.")
    try:
        update_credential_policy(
            db,
            provider_id,
            strategy=req.strategy,
            max_attempts=req.max_attempts,
        )
    except ValueError as exc:
        raise ValidationAppError(str(exc)) from exc
    return _policy_response(provider_id, db)


@router.get(
    "/settings/integrations/{provider_id}/credentials",
    response_model=ProviderCredentialsResponse,
)
def get_provider_credentials(
    provider_id: str,
    db: Session = Depends(get_db),
):
    _provider_or_404(provider_id)
    migrate_legacy_provider_credentials(db)
    return _credential_list_response(provider_id, db)


@router.post(
    "/settings/integrations/{provider_id}/credentials",
    response_model=ProviderCredentialInfo,
)
def add_provider_credential(
    provider_id: str,
    req: CreateProviderCredentialRequest,
    db: Session = Depends(get_db),
):
    _provider_or_404(provider_id)
    if not provider_requires_api_key(provider_id):
        raise ValidationAppError("This provider does not use API credentials.")

    migrate_legacy_provider_credentials(db)
    settings = get_app_settings()
    existing = list_provider_credentials(db, provider_id)
    try:
        credential = create_provider_credential(
            db,
            provider_id=provider_id,
            label=req.label,
            secret=req.secret,
            activate=True if not existing else req.activate,
            max_credentials=settings.max_provider_credentials,
        )
    except CredentialVaultError as exc:
        raise ValidationAppError(str(exc)) from exc
    return _credential_info(credential)


@router.patch(
    "/settings/integrations/{provider_id}/credentials/{credential_id}",
    response_model=ProviderCredentialInfo,
)
def update_provider_credential(
    provider_id: str,
    credential_id: int,
    req: UpdateProviderCredentialRequest,
    db: Session = Depends(get_db),
):
    _provider_or_404(provider_id)
    credential = _credential_or_422(provider_id, credential_id, db)
    try:
        if req.label is not None:
            credential = rename_provider_credential(
                db,
                provider_id,
                credential_id,
                req.label,
            )
        if req.secret is not None:
            credential = replace_provider_credential_secret(
                db,
                provider_id,
                credential_id,
                req.secret,
            )
    except CredentialVaultError as exc:
        raise ValidationAppError(str(exc)) from exc
    return _credential_info(credential)


@router.put(
    "/settings/integrations/{provider_id}/credentials/{credential_id}/activate",
    response_model=ProviderCredentialInfo,
)
def activate_credential(
    provider_id: str,
    credential_id: int,
    db: Session = Depends(get_db),
):
    _provider_or_404(provider_id)
    try:
        credential = activate_provider_credential(db, provider_id, credential_id)
    except CredentialVaultError as exc:
        raise ValidationAppError(str(exc)) from exc
    return _credential_info(credential)


@router.post(
    "/settings/integrations/{provider_id}/credentials/{credential_id}/test",
    response_model=TestConnectionResponse,
)
def test_credential(
    provider_id: str,
    credential_id: int,
    db: Session = Depends(get_db),
):
    provider = _provider_or_404(provider_id)
    credential = _credential_or_422(provider_id, credential_id, db)
    active_model = get_setting(db, "llm_provider") or ""
    saved_model = (
        active_model
        if provider_from_model(active_model) == provider_id
        else get_setting(db, f"selected_model_{provider_id}")
    )
    model_id = saved_model or provider.models[0].id
    result = test_provider_connection(
        model_id,
        decrypt_provider_credential(credential),
        failure_message="Provider connection failed.",
    )
    credential.last_tested_at = datetime.now(UTC)
    credential.health_status = "healthy" if result.ok else "unhealthy"
    credential.consecutive_failures = (
        0 if result.ok else credential.consecutive_failures + 1
    )
    db.commit()
    return result


@router.delete(
    "/settings/integrations/{provider_id}/credentials/{credential_id}",
    response_model=ProviderCredentialsResponse,
)
def delete_credential(
    provider_id: str,
    credential_id: int,
    db: Session = Depends(get_db),
):
    _provider_or_404(provider_id)
    try:
        delete_provider_credential(db, provider_id, credential_id)
    except CredentialVaultError as exc:
        raise ValidationAppError(str(exc)) from exc
    return _credential_list_response(provider_id, db)


@router.delete(
    "/settings/integrations/{provider_id}",
    response_model=CredentialIntegrationsResponse,
)
def disconnect_provider(provider_id: str, db: Session = Depends(get_db)):
    """Remove all saved configuration for a provider."""
    _provider_or_404(provider_id)
    clear_provider_api_key(db, provider_id)
    clear_provider_base_url(db, provider_id)
    set_setting(db, f"selected_model_{provider_id}", "")

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
                credential_url=credential_url_for_provider(provider.id),
                supports_custom_models=supports_custom_models(provider.id),
                requires_api_key=provider_requires_api_key(provider.id),
                models=[
                    ModelOption(
                        value=model.id,
                        label=model.label,
                        status=model.status.value,
                        capabilities=sorted(
                            capability.value for capability in model.capabilities
                        ),
                        traits=sorted(trait.value for trait in model.traits),
                        free_tier=model.free_tier,
                    )
                    for model in provider.models
                ],
            )
            for provider in CATALOG.providers
        ]
    )
