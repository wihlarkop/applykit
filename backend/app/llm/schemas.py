from typing import Literal

from pydantic import BaseModel


class ModelOption(BaseModel):
    value: str
    label: str
    status: Literal["stable", "preview", "experimental"]
    capabilities: list[str]
    traits: list[str]
    free_tier: bool


class ProviderInfo(BaseModel):
    id: str
    label: str
    auth_type: Literal["api_key", "token", "none"]
    local: bool
    credential_url: str | None
    supports_custom_models: bool
    models: list[ModelOption]
    requires_api_key: bool


class ModelsResponse(BaseModel):
    providers: list[ProviderInfo]
