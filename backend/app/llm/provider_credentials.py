from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator

try:
    from yaml import CSafeLoader as CredentialSafeLoader
except ImportError:  # pragma: no cover - platform dependent
    from yaml import SafeLoader as CredentialSafeLoader


CREDENTIAL_LINKS_PATH = Path(__file__).with_name("provider_credentials.yaml")


class ProviderCredentialLinks(BaseModel):
    model_config = ConfigDict(frozen=True)

    providers: dict[str, HttpUrl]

    @field_validator("providers")
    @classmethod
    def links_use_https(cls, providers: dict[str, HttpUrl]) -> dict[str, HttpUrl]:
        for provider_id, url in providers.items():
            if url.scheme != "https":
                raise ValueError(f"credential URL for {provider_id} must use HTTPS")
        return providers


def load_provider_credential_links(
    path: Path = CREDENTIAL_LINKS_PATH,
) -> ProviderCredentialLinks:
    with path.open("r", encoding="utf-8") as stream:
        raw: Any = yaml.load(stream, Loader=CredentialSafeLoader)
    if not isinstance(raw, dict):
        raise ValueError("provider credential links root must be a mapping")
    return ProviderCredentialLinks.model_validate(raw)


CREDENTIAL_LINKS = load_provider_credential_links()


def credential_url_for_provider(provider_id: str) -> str | None:
    url = CREDENTIAL_LINKS.providers.get(provider_id)
    return str(url) if url else None
