# LLM catalog

`catalog.yaml` is the release-managed source of truth for supported providers and active text/chat models. The catalog is loaded with PyYAML's safe loader and validated by immutable Pydantic models at backend startup.

OpenRouter and Hugging Face intentionally contain a smaller curated selection to keep the Settings UI usable. Update this catalog as part of an ApplyKit release when providers add, preview, or deprecate models.
