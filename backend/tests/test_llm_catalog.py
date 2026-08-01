from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.llm.catalog import CATALOG, load_catalog
from app.llm.models import CatalogDefinition
from app.llm.validate_catalog import build_report


EXPECTED_PROVIDERS = {
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


def test_catalog_contains_expected_providers() -> None:
    assert {provider.id for provider in CATALOG.providers} == EXPECTED_PROVIDERS


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


def test_every_provider_has_verification_metadata() -> None:
    for provider in CATALOG.providers:
        assert str(provider.documentation_url).startswith("https://")
        assert provider.last_verified <= date.today()


def test_catalog_does_not_include_deprecated_markers() -> None:
    blocked_markers = {"deprecated", "retired", "shutdown", "shut down"}
    for provider in CATALOG.providers:
        for model in provider.models:
            searchable = f"{model.id} {model.label}".casefold()
            assert not any(marker in searchable for marker in blocked_markers)


def test_openrouter_and_huggingface_are_intentionally_curated() -> None:
    providers = {provider.id: provider for provider in CATALOG.providers}
    assert 10 <= len(providers["openrouter"].models) <= 15
    assert 10 <= len(providers["huggingface"].models) <= 15


def test_known_retired_gemini_preview_is_absent() -> None:
    gemini = next(provider for provider in CATALOG.providers if provider.id == "gemini")
    assert "gemini/gemini-3.1-flash-lite-preview" not in {
        model.id for model in gemini.models
    }


def test_groq_production_text_models_are_present() -> None:
    groq = next(provider for provider in CATALOG.providers if provider.id == "groq")
    model_ids = {model.id for model in groq.models}
    assert {
        "groq/llama-3.1-8b-instant",
        "groq/llama-3.3-70b-versatile",
        "groq/openai/gpt-oss-20b",
        "groq/openai/gpt-oss-120b",
    } <= model_ids


def test_validator_report_summarizes_catalog() -> None:
    report = build_report(CATALOG)
    assert report.provider_count == len(EXPECTED_PROVIDERS)
    assert report.model_count > report.provider_count
    assert report.preview_count >= 1
    assert report.oldest_verification <= date.today()


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
                        "documentation_url": "https://ollama.com/library",
                        "last_verified": "2026-08-02",
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


def test_catalog_rejects_insecure_documentation_url() -> None:
    with pytest.raises(ValidationError, match="documentation URL must use HTTPS"):
        CatalogDefinition.model_validate(
            {
                "providers": [
                    {
                        "id": "example",
                        "label": "Example",
                        "model_prefix": "example",
                        "auth_type": "api_key",
                        "documentation_url": "http://example.com/models",
                        "last_verified": "2026-08-02",
                        "models": [
                            {
                                "id": "example/chat",
                                "label": "Chat",
                                "capabilities": ["text"],
                            }
                        ],
                    }
                ]
            }
        )


def test_catalog_rejects_future_verification_date() -> None:
    with pytest.raises(ValidationError, match="last_verified cannot be in the future"):
        CatalogDefinition.model_validate(
            {
                "providers": [
                    {
                        "id": "example",
                        "label": "Example",
                        "model_prefix": "example",
                        "auth_type": "api_key",
                        "documentation_url": "https://example.com/models",
                        "last_verified": "2999-01-01",
                        "models": [
                            {
                                "id": "example/chat",
                                "label": "Chat",
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
