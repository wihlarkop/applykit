from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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
    def requires_text_capability(self):
        if Capability.TEXT not in self.capabilities:
            raise ValueError("catalog models must support text")
        return self


class ProviderDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    model_prefix: str
    auth_type: AuthType
    local: bool = False
    models: tuple[ModelDefinition, ...]

    @field_validator("id", "label", "model_prefix")
    @classmethod
    def non_empty_string(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("models")
    @classmethod
    def models_are_sorted(cls, models: tuple[ModelDefinition, ...]):
        labels = [model.label.casefold() for model in models]
        if labels != sorted(labels):
            raise ValueError("provider models must be sorted alphabetically")
        return models

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
    def providers_are_sorted(cls, providers: tuple[ProviderDefinition, ...]):
        labels = [provider.label.casefold() for provider in providers]
        if labels != sorted(labels):
            raise ValueError("providers must be sorted alphabetically")
        return providers

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
        return self
