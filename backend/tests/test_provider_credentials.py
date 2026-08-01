from app.llm.catalog import CATALOG
from app.llm.provider_credentials import (
    CREDENTIAL_LINKS,
    credential_url_for_provider,
)


def test_every_remote_provider_has_an_https_credential_url() -> None:
    remote_provider_ids = {
        provider.id for provider in CATALOG.providers if provider.auth_type != "none"
    }

    assert set(CREDENTIAL_LINKS.providers) == remote_provider_ids
    for provider_id in remote_provider_ids:
        assert credential_url_for_provider(provider_id).startswith("https://")


def test_local_provider_has_no_credential_url() -> None:
    assert credential_url_for_provider("ollama") is None


def test_unknown_provider_has_no_credential_url() -> None:
    assert credential_url_for_provider("unknown") is None
