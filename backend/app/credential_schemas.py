from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CredentialIntegrationInfo(BaseModel):
    id: str
    label: str
    is_active: bool
    api_key_configured: bool
    masked_api_key: str | None
    current_model: str | None
    credential_count: int = 0
    active_credential_id: int | None = None
    active_credential_label: str | None = None
    credential_strategy: Literal["manual", "failover", "round_robin"] = "manual"


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
    secret: str = Field(min_length=1, max_length=4096)
    activate: bool = False


class UpdateProviderCredentialRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    secret: str | None = Field(default=None, min_length=1, max_length=4096)
