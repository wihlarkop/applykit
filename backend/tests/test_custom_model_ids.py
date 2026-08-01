import pytest

from app.llm.model_selection import (
    CUSTOM_MODEL_PROVIDERS,
    validate_model_id,
)


def test_catalog_model_is_accepted() -> None:
    assert validate_model_id("openai/gpt-5-mini") == "openai/gpt-5-mini"


@pytest.mark.parametrize(
    "model_id",
    [
        "openrouter/google/gemini-2.5-flash:free",
        "huggingface/meta-llama/Llama-3.3-70B-Instruct",
        "ollama/qwen3:14b",
    ],
)
def test_supported_provider_custom_model_is_accepted(model_id: str) -> None:
    assert validate_model_id(model_id) == model_id


def test_custom_model_providers_are_explicit() -> None:
    assert CUSTOM_MODEL_PROVIDERS == frozenset({"openrouter", "huggingface", "ollama"})


@pytest.mark.parametrize(
    ("model_id", "message"),
    [
        ("", "must not be empty"),
        ("openrouter/model with spaces", "must not contain whitespace"),
        ("openrouter/model\nnext", "must not contain whitespace"),
        ("openai/not-in-catalog", "does not allow custom model IDs"),
        ("unknown/model", "Unknown provider"),
        ("openrouter", "must include a provider prefix"),
        ("openrouter/" + "x" * 200, "must be at most 200 characters"),
    ],
)
def test_invalid_custom_model_is_rejected(model_id: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_model_id(model_id)
