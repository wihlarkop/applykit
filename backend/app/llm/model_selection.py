from __future__ import annotations

from app.llm.catalog import CATALOG, get_provider


CUSTOM_MODEL_PROVIDERS = frozenset({"openrouter", "huggingface", "ollama"})
MAX_MODEL_ID_LENGTH = 200

_CATALOG_MODEL_IDS = frozenset(
    model.id for provider in CATALOG.providers for model in provider.models
)


def supports_custom_models(provider_id: str) -> bool:
    return provider_id in CUSTOM_MODEL_PROVIDERS


def validate_model_id(model_id: str) -> str:
    normalized = model_id.strip()
    if not normalized:
        raise ValueError("Model ID must not be empty.")
    if len(normalized) > MAX_MODEL_ID_LENGTH:
        raise ValueError(
            f"Model ID must be at most {MAX_MODEL_ID_LENGTH} characters."
        )
    if any(character.isspace() for character in normalized):
        raise ValueError("Model ID must not contain whitespace.")
    if "/" not in normalized:
        raise ValueError("Model ID must include a provider prefix.")

    provider_id, model_name = normalized.split("/", 1)
    provider = get_provider(provider_id)
    if provider is None:
        raise ValueError(f"Unknown provider: {provider_id}.")
    if not model_name:
        raise ValueError("Model ID must include a model name after the provider prefix.")

    if normalized in _CATALOG_MODEL_IDS:
        return normalized
    if not supports_custom_models(provider_id):
        raise ValueError(f"Provider {provider_id} does not allow custom model IDs.")

    expected_prefix = f"{provider.model_prefix}/"
    if not normalized.startswith(expected_prefix):
        raise ValueError(f"Model ID must start with {expected_prefix}.")
    return normalized
