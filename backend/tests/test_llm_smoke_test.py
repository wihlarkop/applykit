from types import SimpleNamespace

import pytest

from app.llm.smoke_test import (
    SmokeResult,
    credential_env_var,
    resolve_smoke_model,
    run_smoke_test,
)


def test_credential_env_var_uses_provider_specific_names():
    assert credential_env_var("gemini") == "GEMINI_API_KEY"
    assert credential_env_var("huggingface") == "HF_TOKEN"
    assert credential_env_var("ollama") is None


def test_resolve_smoke_model_prefers_stable_free_or_low_cost_model():
    model = resolve_smoke_model("gemini")

    assert model.startswith("gemini/")


def test_resolve_smoke_model_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        resolve_smoke_model("missing")


def test_run_smoke_test_skips_when_required_credential_is_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = run_smoke_test("openai", completion=lambda **_: None)

    assert result.status == "SKIP"
    assert result.provider_id == "openai"
    assert result.credential_env == "OPENAI_API_KEY"
    assert "OPENAI_API_KEY" in result.message


def test_run_smoke_test_passes_key_without_exposing_it(monkeypatch):
    secret = "sk-super-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    captured = {}

    def completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    result = run_smoke_test("openai", completion=completion)

    assert result.status == "PASS"
    assert captured["api_key"] == secret
    assert secret not in result.message
    assert captured["max_tokens"] == 3
    assert captured["timeout"] == 20


def test_run_smoke_test_never_includes_exception_message(monkeypatch):
    secret = "secret-token-value"
    monkeypatch.setenv("GROQ_API_KEY", secret)

    def completion(**_):
        raise RuntimeError(f"request failed with {secret}")

    result = run_smoke_test("groq", completion=completion)

    assert result.status == "FAIL"
    assert result.error_type == "RuntimeError"
    assert secret not in result.message
    assert "request failed" not in result.message


def test_run_smoke_test_supports_keyless_ollama(monkeypatch):
    captured = {}

    def completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    result = run_smoke_test("ollama", model_id="ollama/llama3.2", completion=completion)

    assert result == SmokeResult(
        status="PASS",
        provider_id="ollama",
        model_id="ollama/llama3.2",
        message="Connection successful.",
    )
    assert "api_key" not in captured


def test_run_smoke_test_rejects_model_from_another_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    with pytest.raises(ValueError, match="must start with openai/"):
        run_smoke_test(
            "openai",
            model_id="gemini/gemini-2.5-flash",
            completion=lambda **_: None,
        )
