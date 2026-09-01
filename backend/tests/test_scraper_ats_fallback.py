import asyncio

from app.services import scraper


def test_greenhouse_failure_falls_through_to_jina(monkeypatch):
    """A transient Greenhouse API failure should not fail the whole scrape."""
    call_count = 0

    async def failing_greenhouse(url, client):
        nonlocal call_count
        call_count += 1
        raise TimeoutError("upstream timed out")

    async def fake_jina(url, client):
        return "Jina markdown content"

    async def unexpected_crawl4ai(url):
        raise AssertionError("crawl4ai should not run once jina succeeds")

    monkeypatch.setattr(scraper, "validate_public_http_url", lambda url: _noop(), raising=False)
    monkeypatch.setattr(scraper, "_scrape_greenhouse", failing_greenhouse)
    monkeypatch.setattr(scraper, "_scrape_jina", fake_jina)
    monkeypatch.setattr(scraper, "_scrape_crawl4ai", unexpected_crawl4ai)

    result = asyncio.run(
        scraper.scrape_job_url(
            "https://job-boards.greenhouse.io/appier/jobs/8102255", object()
        )
    )

    assert call_count == 2, "should retry once before giving up"
    assert result.source == "jina"
    assert result.job_description == "Jina markdown content"


def test_greenhouse_url_shape_mismatch_does_not_retry(monkeypatch):
    """A URL that doesn't match the expected Greenhouse shape should fail fast."""
    call_count = 0

    async def bad_shape_greenhouse(url, client):
        nonlocal call_count
        call_count += 1
        raise ValueError("Could not parse Greenhouse URL")

    async def fake_jina(url, client):
        return "Jina markdown content"

    monkeypatch.setattr(scraper, "validate_public_http_url", lambda url: _noop(), raising=False)
    monkeypatch.setattr(scraper, "_scrape_greenhouse", bad_shape_greenhouse)
    monkeypatch.setattr(scraper, "_scrape_jina", fake_jina)

    result = asyncio.run(
        scraper.scrape_job_url("https://greenhouse.io/not-a-job-url", object())
    )

    assert call_count == 1, "URL shape mismatches should not be retried"
    assert result.source == "jina"


def test_greenhouse_success_is_returned_without_falling_through(monkeypatch):
    async def working_greenhouse(url, client):
        return scraper.ScrapedJob(
            job_description="Role details",
            company_name="Appier",
            role_title="AI Engineer",
            location="Tokyo, Japan",
            salary=None,
            source="greenhouse_api",
        )

    async def unexpected_jina(url, client):
        raise AssertionError("jina should not run when greenhouse succeeds")

    monkeypatch.setattr(scraper, "validate_public_http_url", lambda url: _noop(), raising=False)
    monkeypatch.setattr(scraper, "_scrape_greenhouse", working_greenhouse)
    monkeypatch.setattr(scraper, "_scrape_jina", unexpected_jina)

    result = asyncio.run(
        scraper.scrape_job_url(
            "https://job-boards.greenhouse.io/appier/jobs/8102255", object()
        )
    )

    assert result.source == "greenhouse_api"
    assert result.company_name == "Appier"


async def _noop():
    return None
