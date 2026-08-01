from datetime import date, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator, model_validator


class ModelStatus(StrEnum):
    STABLE = "stable"
    PREVIEW = "preview"
    EXPERIMENTAL = "experimental"


class AuthType(StrEnum):
    API_KEY = "api_key"
    TOKEN = "token"
    NONE = "none"


class Capability(StrEnum):
    TEXT = "text"
    STREAMING = "streaming"
    STRUCTURED_OUTPUT = "structured_output"


class ModelTrait(StrEnum):
    FAST = "fast"
    LOW_COST = "low_cost"
    HIGH_QUALITY = "high_quality"
    LOCAL = "local"
    REASONING = "reasoning"


class ModelDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    status: ModelStatus = ModelStatus.STABLE
    capabilities: frozenset[Capability]
    traits: frozenset[ModelTrait] = frozenset()
    free_tier: bool = False

    @field_validator("id", "label")
    @classmethod
    def non_empty_string(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def validate_model_semantics(self):
        if Capability.TEXT not in self.capabilities:
            raise ValueError("catalog models must support text")

        searchable = f"{self.id} {self.label}".casefold()
        blocked_markers = ("deprecated", "retired", "shutdown", "shut down")
        if any(marker in searchable for marker in blocked_markers):
            raise ValueError("deprecated models cannot appear in the active catalog")
        return self


class ProviderDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    model_prefix: str
    auth_type: AuthType
    documentation_url: HttpUrl
    last_verified: date
    local: bool = False
    models: tuple[ModelDefinition, ...]

    @field_validator("id", "label", "model_prefix")
    @classmethod
    def non_empty_string(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("documentation_url")
    @classmethod
    def documentation_url_uses_https(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("documentation URL must use HTTPS")
        return value

    @field_validator("last_verified")
    @classmethod
    def verification_date_is_not_future(cls, value: date) -> date:
        # Allow a one-day boundary because release authors and CI runners may be
        # in different timezones around midnight.
        if value > date.today() + timedelta(days=1):
            raise ValueError("last_verified cannot be in the future")
        return value

    @field_validator("models")
    @classmethod
    def sort_models(cls, models: tuple[ModelDefinition, ...]):
        return tuple(sorted(models, key=lambda model: model.label.casefold()))

    @model_validator(mode="after")
    def validate_provider_semantics(self):
        if not self.models:
            raise ValueError("provider must define at least one model")
        if self.auth_type == AuthType.NONE and not self.local:
            raise ValueError("keyless providers must be local")
        if self.local and self.auth_type != AuthType.NONE:
            raise ValueError("local providers must be keyless")

        expected_prefix = f"{self.model_prefix}/"
        for model in self.models:
            if not model.id.startswith(expected_prefix):
                raise ValueError(
                    f"model {model.id!r} must start with {expected_prefix!r}"
                )
            if self.local and ModelTrait.LOCAL not in model.traits:
                raise ValueError("local provider models must have the local trait")
            if not self.local and ModelTrait.LOCAL in model.traits:
                raise ValueError("remote provider models cannot have the local trait")
        return self


class CatalogDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    providers: tuple[ProviderDefinition, ...]

    @field_validator("providers")
    @classmethod
    def sort_providers(cls, providers: tuple[ProviderDefinition, ...]):
        return tuple(sorted(providers, key=lambda provider: provider.label.casefold()))

    @model_validator(mode="after")
    def validate_uniqueness(self):
        provider_ids = [provider.id for provider in self.providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider IDs must be unique")

        model_ids = [
            model.id
            for provider in self.providers
            for model in provider.models
        ]
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("model IDs must be globally unique")

        curated_limits = {"openrouter": 15, "huggingface": 15}
        for provider in self.providers:
            limit = curated_limits.get(provider.id)
            if limit is not None and len(provider.models) > limit:
                raise ValueError(f"{provider.id} catalog cannot exceed {limit} models")
        return self
