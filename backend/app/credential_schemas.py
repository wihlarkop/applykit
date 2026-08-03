from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

CredentialStrategyName = Literal["manual", "failover", "round_robin"]


class CredentialSecret(SecretStr):
    """Secret string compatible with existing narrow `.strip()` boundaries."""

    def strip(self) -> str:
        return self.get_secret_value().strip()


def _validate_secret_length(
    value: CredentialSecret | None,
) -> CredentialSecret | None:
    if value is None:
        return None
    length = len(value.get_secret_value())
    if length < 1:
        raise ValueError("Credential secret is required.")
    if length > 4096:
        raise ValueError("Credential secret must be 4096 characters or fewer.")
    return value


class ProviderSettingsRequest(BaseModel):
    model: str
    api_key: CredentialSecret | None = None
    activate: bool = True
    base_url: str | None = None

    _validate_api_key = field_validator("api_key")(_validate_secret_length)


class CredentialIntegrationInfo(BaseModel):
    id: str
    label: str
    is_active: bool
    api_key_configured: bool
    masked_api_key: str | None
    current_model: str | None
    base_url: str | None = None
    credential_count: int = 0
    active_credential_id: int | None = None
    active_credential_label: str | None = None
    credential_strategy: CredentialStrategyName = "manual"


class CredentialIntegrationsResponse(BaseModel):
    integrations: list[CredentialIntegrationInfo]


class ProviderCredentialInfo(BaseModel):
    id: int
    provider_id: str
    label: str
    masked_secret: str
    is_active: bool
    is_enabled: bool
    priority: int
    health_status: str
    cooldown_until: datetime | None
    last_tested_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderCredentialsResponse(BaseModel):
    provider_id: str
    credentials: list[ProviderCredentialInfo]
    max_credentials: int


class CreateProviderCredentialRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    secret: CredentialSecret
    activate: bool = False

    _validate_secret = field_validator("secret")(_validate_secret_length)


class UpdateProviderCredentialRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    secret: CredentialSecret | None = None

    _validate_secret = field_validator("secret")(_validate_secret_length)


class CredentialPolicyResponse(BaseModel):
    provider_id: str
    strategy: CredentialStrategyName
    max_attempts: int


class UpdateCredentialPolicyRequest(BaseModel):
    strategy: CredentialStrategyName
    max_attempts: int = Field(default=2, ge=1, le=5)
