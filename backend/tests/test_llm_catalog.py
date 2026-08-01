from pathlib import Path

import pytest
from pydantic import ValidationError

from app.llm.catalog import CATALOG, load_catalog
from app.llm.models import CatalogDefinition


def test_catalog_contains_expected_providers() -> None:
    assert {provider.id for provider in CATALOG.providers} == {
        "anthropic",
        "deepseek",
        "gemini",
        "groq",
        "huggingface",
        "mistral",
        "ollama",
        "openai",
        "openrouter",
        "xai",
    }


def test_catalog_provider_and_model_labels_are_sorted() -> None:
    provider_labels = [provider.label.casefold() for provider in CATALOG.providers]
    assert provider_labels == sorted(provider_labels)

    for provider in CATALOG.providers:
        model_labels = [model.label.casefold() for model in provider.models]
        assert model_labels == sorted(model_labels)


def test_catalog_model_ids_are_globally_unique() -> None:
    model_ids = [
        model.id
        for provider in CATALOG.providers
        for model in provider.models
    ]
    assert len(model_ids) == len(set(model_ids))


def test_every_catalog_model_supports_text() -> None:
    for provider in CATALOG.providers:
        for model in provider.models:
            assert "text" in model.capabilities


def test_only_ollama_is_keyless_and_local() -> None:
    for provider in CATALOG.providers:
        if provider.id == "ollama":
            assert provider.auth_type == "none"
            assert provider.local is True
        else:
            assert provider.auth_type in {"api_key", "token"}
            assert provider.local is False


def test_openrouter_and_huggingface_are_intentionally_curated() -> None:
    providers = {provider.id: provider for provider in CATALOG.providers}
    assert 10 <= len(providers["openrouter"].models) <= 15
    assert 10 <= len(providers["huggingface"].models) <= 15


def test_invalid_catalog_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CatalogDefinition.model_validate(
            {
                "providers": [
                    {
                        "id": "ollama",
                        "label": "Ollama",
                        "model_prefix": "ollama",
                        "auth_type": "none",
                        "local": True,
                        "models": [
                            {
                                "id": "wrong/model",
                                "label": "Wrong Model",
                                "status": "stable",
                                "capabilities": ["text"],
                            }
                        ],
                    }
                ]
            }
        )


def test_load_catalog_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_text("- invalid\n", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a mapping"):
        load_catalog(path)
