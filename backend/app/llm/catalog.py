from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.llm.models import CatalogDefinition, ProviderDefinition

try:
    from yaml import CSafeLoader as CatalogSafeLoader
except ImportError:  # pragma: no cover - depends on platform wheel availability
    from yaml import SafeLoader as CatalogSafeLoader


CATALOG_PATH = Path(__file__).with_name("catalog.yaml")


def load_catalog(path: Path = CATALOG_PATH) -> CatalogDefinition:
    with path.open("r", encoding="utf-8") as stream:
        raw: Any = yaml.load(stream, Loader=CatalogSafeLoader)
    if not isinstance(raw, dict):
        raise ValueError("LLM catalog root must be a mapping")
    return CatalogDefinition.model_validate(raw)


CATALOG = load_catalog()


@lru_cache(maxsize=1)
def provider_index() -> dict[str, ProviderDefinition]:
    return {provider.id: provider for provider in CATALOG.providers}


@lru_cache(maxsize=1)
def model_index() -> dict[str, str]:
    return {
        model.id: provider.id
        for provider in CATALOG.providers
        for model in provider.models
    }


def get_provider(provider_id: str | None) -> ProviderDefinition | None:
    if not provider_id:
        return None
    return provider_index().get(provider_id)


def get_provider_models(provider_id: str) -> tuple[str, ...]:
    provider = get_provider(provider_id)
    if not provider:
        return ()
    return tuple(model.id for model in provider.models)


def provider_from_model(model_id: str) -> str | None:
    if not model_id:
        return None

    known_provider = model_index().get(model_id)
    if known_provider:
        return known_provider

    # Keep persisted models from older ApplyKit releases attributable to their
    # provider, even when they are no longer offered in the active catalog.
    for provider in CATALOG.providers:
        if model_id == provider.model_prefix or model_id.startswith(
            f"{provider.model_prefix}/"
        ):
            return provider.id
    return None


def provider_requires_api_key(provider_id: str | None) -> bool:
    provider = get_provider(provider_id)
    return provider is None or provider.auth_type != "none"
