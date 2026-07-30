import asyncio

import pytest

from app.services import scraper
from app.services.url_security import UnsafeUrlError


def test_scraper_validates_url_before_any_network_fallback(monkeypatch):
    """Unsafe targets must be rejected before Jina or Crawl4AI can run."""

    async def reject_private_url(url: str):
        raise UnsafeUrlError("URL resolves to a non-public address")

    async def unexpected_network_call(*args, **kwargs):
        raise AssertionError("network fallback ran before URL validation")

    monkeypatch.setattr(
        scraper,
        "validate_public_http_url",
        reject_private_url,
        raising=False,
    )
    monkeypatch.setattr(scraper, "_scrape_jina", unexpected_network_call)
    monkeypatch.setattr(scraper, "_scrape_crawl4ai", unexpected_network_call)

    with pytest.raises(UnsafeUrlError):
        asyncio.run(scraper.scrape_job_url("http://localhost/admin", object()))
