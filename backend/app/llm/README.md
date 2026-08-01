# LLM catalog

`catalog.yaml` is the release-managed source of truth for supported providers and active text/chat models. The catalog is loaded with PyYAML's safe loader and validated by immutable Pydantic models at backend startup.

OpenRouter and Hugging Face intentionally contain a smaller curated selection to keep the Settings UI usable. Update this catalog as part of an ApplyKit release when providers add, preview, or deprecate models.

Each provider must include:

- an official HTTPS `documentation_url`
- a `last_verified` date
- only active text/chat model identifiers that match the LiteLLM provider prefix

Run the local validation command after editing the catalog:

```bash
cd backend
uv run python -m app.llm.validate_catalog
```

CI can additionally reject stale verification metadata:

```bash
uv run python -m app.llm.validate_catalog --max-age-days 120
```

The command validates the YAML through Pydantic and prints provider, model, preview, experimental, free-tier, and verification-date totals. It does not call provider APIs and does not require API keys.
