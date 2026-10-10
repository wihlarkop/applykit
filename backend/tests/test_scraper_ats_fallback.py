import asyncio

import httpx
import pytest

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

    monkeypatch.setattr(
        scraper, "validate_public_http_url", lambda url: _noop(), raising=False
    )
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

    monkeypatch.setattr(
        scraper, "validate_public_http_url", lambda url: _noop(), raising=False
    )
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

    monkeypatch.setattr(
        scraper, "validate_public_http_url", lambda url: _noop(), raising=False
    )
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


@pytest.mark.parametrize(
    ("status", "expected_attempts"),
    [
        (400, 1),
        (401, 1),
        (403, 1),
        (404, 1),
        (429, 1),
        (501, 1),
        (408, 2),
        (500, 2),
        (502, 2),
        (503, 2),
        (504, 2),
    ],
)
def test_http_failure_retry_policy(status, expected_attempts):
    calls = 0

    async def failing_handler(url, client):
        nonlocal calls
        calls += 1
        response = httpx.Response(status, request=httpx.Request("GET", url))
        response.raise_for_status()

    result = asyncio.run(
        scraper._try_ats_api(failing_handler, "https://example.com/job", object())
    )

    assert result is None
    assert calls == expected_attempts


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ReadTimeout("timeout"),
        httpx.ConnectError("connection failed"),
        httpx.RemoteProtocolError("upstream disconnected"),
        TimeoutError("timeout"),
    ],
)
def test_transient_transport_failure_can_recover(failure):
    calls = 0
    expected = scraper.ScrapedJob(
        "Role details", "Acme", "Engineer", None, None, "lever_api"
    )

    async def recovering_handler(url, client):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise failure
        return expected

    result = asyncio.run(
        scraper._try_ats_api(recovering_handler, "https://example.com/job", object())
    )

    assert result is expected
    assert calls == 2


@pytest.mark.parametrize(
    "failure",
    [
        ValueError("invalid JSON"),
        KeyError("missing field"),
        httpx.UnsupportedProtocol("unsupported protocol"),
    ],
)
def test_non_transient_failure_falls_through_without_retry(failure):
    calls = 0

    async def failing_handler(url, client):
        nonlocal calls
        calls += 1
        raise failure

    result = asyncio.run(
        scraper._try_ats_api(failing_handler, "https://example.com/job", object())
    )

    assert result is None
    assert calls == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://job-boards.greenhouse.io/acme/jobs/123",
        "https://jobs.lever.co/acme/abc",
        "https://jobs.ashbyhq.com/acme/jobs/abc",
    ],
)
@pytest.mark.parametrize(
    ("status", "expected_attempts"), [(404, 1), (429, 1), (503, 2)]
)
def test_ats_http_failure_reaches_generic_fallback(
    monkeypatch, url, status, expected_attempts
):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status)

    async def fake_jina(job_url, client):
        assert job_url == url
        return "Fallback job description"

    async def unexpected_crawl4ai(job_url):
        raise AssertionError("Crawl4AI must not run after Jina succeeds")

    monkeypatch.setattr(scraper, "validate_public_http_url", lambda url: _noop())
    monkeypatch.setattr(scraper, "_scrape_jina", fake_jina)
    monkeypatch.setattr(scraper, "_scrape_crawl4ai", unexpected_crawl4ai)

    async def scrape():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await scraper.scrape_job_url(url, client)

    result = asyncio.run(scrape())

    assert result.source == "jina"
    assert result.job_description == "Fallback job description"
    assert len(requests) == expected_attempts
