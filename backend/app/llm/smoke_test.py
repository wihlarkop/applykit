from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Callable, Literal

from app.llm.catalog import get_provider

SmokeStatus = Literal["PASS", "FAIL", "SKIP"]
CompletionCallable = Callable[..., object]

_CREDENTIAL_ENV_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "huggingface": "HF_TOKEN",
    "mistral": "MISTRAL_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "xai": "XAI_API_KEY",
}


@dataclass(frozen=True)
class SmokeResult:
    status: SmokeStatus
    provider_id: str
    model_id: str
    message: str
    credential_env: str | None = None
    error_type: str | None = None


def credential_env_var(provider_id: str) -> str | None:
    return _CREDENTIAL_ENV_VARS.get(provider_id)


def resolve_smoke_model(provider_id: str) -> str:
    provider = get_provider(provider_id)
    if provider is None:
        raise ValueError(f"Unknown provider: {provider_id}.")

    stable_models = [model for model in provider.models if model.status.value == "stable"]
    candidates = stable_models or list(provider.models)
    if not candidates:
        raise ValueError(f"Provider {provider_id} has no catalog models.")

    def priority(model) -> tuple[int, int, str]:
        traits = {trait.value for trait in model.traits}
        return (
            0 if model.free_tier else 1,
            0 if "low_cost" in traits else 1,
            model.label.casefold(),
        )

    return min(candidates, key=priority).id


def run_smoke_test(
    provider_id: str,
    *,
    model_id: str | None = None,
    completion: CompletionCallable | None = None,
) -> SmokeResult:
    provider = get_provider(provider_id)
    if provider is None:
        raise ValueError(f"Unknown provider: {provider_id}.")

    selected_model = model_id or resolve_smoke_model(provider_id)
    expected_prefix = f"{provider_id}/"
    if not selected_model.startswith(expected_prefix):
        raise ValueError(
            f"Model ID for provider {provider_id} must start with {expected_prefix}"
        )

    env_name = credential_env_var(provider_id)
    api_key = os.environ.get(env_name, "").strip() if env_name else ""
    if provider.auth_type.value != "none" and not api_key:
        return SmokeResult(
            status="SKIP",
            provider_id=provider_id,
            model_id=selected_model,
            credential_env=env_name,
            message=f"Credential is not set in {env_name}.",
        )

    if completion is None:
        import litellm

        completion = litellm.completion

    request_kwargs: dict[str, object] = {
        "model": selected_model,
        "messages": [{"role": "user", "content": "Reply exactly: ok"}],
        "timeout": 20,
        "max_tokens": 3,
    }
    if api_key:
        request_kwargs["api_key"] = api_key

    try:
        response = completion(**request_kwargs)
        choices = getattr(response, "choices", None) or []
        content = getattr(getattr(choices[0], "message", None), "content", "") if choices else ""
        if not content:
            return SmokeResult(
                status="FAIL",
                provider_id=provider_id,
                model_id=selected_model,
                message="Provider returned an empty response.",
            )
        return SmokeResult(
            status="PASS",
            provider_id=provider_id,
            model_id=selected_model,
            message="Connection successful.",
        )
    except Exception as exc:
        return SmokeResult(
            status="FAIL",
            provider_id=provider_id,
            model_id=selected_model,
            error_type=type(exc).__name__,
            message="Provider request failed. See the error type for diagnosis.",
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a minimal live LiteLLM smoke test for one provider."
    )
    parser.add_argument(
        "--provider",
        required=True,
        help="Provider ID from the ApplyKit catalog, for example gemini or openai.",
    )
    parser.add_argument(
        "--model",
        help="Optional full LiteLLM model ID. It must match the selected provider prefix.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = run_smoke_test(args.provider, model_id=args.model)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 2

    suffix = f" ({result.error_type})" if result.error_type else ""
    print(
        f"{result.status} provider={result.provider_id} "
        f"model={result.model_id}: {result.message}{suffix}"
    )
    if result.status == "PASS":
        return 0
    if result.status == "SKIP":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
