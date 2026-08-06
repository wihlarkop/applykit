import asyncio

from app.routes import scrape
from app.schemas import ParseJobDescriptionResponse, ScrapeAnalyzeRequest
from app.services.scraper import ScrapedJob


def test_pasted_job_url_uses_scraper_and_preserves_authoritative_metadata(monkeypatch):
    job_url = "https://job-boards.greenhouse.io/appier/jobs/8102255"
    scraped_urls: list[str] = []

    async def fake_scrape_job_url(url: str, client) -> ScrapedJob:
        scraped_urls.append(url)
        return ScrapedJob(
            job_description="AI Engineer, Playable Ads - Tokyo Japan.\n\nRole details",
            company_name="Appier",
            role_title="AI Engineer, Playable Ads - Tokyo Japan.",
            location="Tokyo, Japan",
            salary=None,
            source="greenhouse_api",
        )

    def fake_parse_job_description(*args, **kwargs) -> ParseJobDescriptionResponse:
        return ParseJobDescriptionResponse(
            company_name="Appier",
            role_title="Senior Data Scientist",
            location="Taipei, Taiwan",
            salary=None,
        )

    monkeypatch.setattr(scrape, "require_llm_config", lambda db: ("openai", "secret"))
    monkeypatch.setattr(scrape, "scrape_job_url", fake_scrape_job_url)
    monkeypatch.setattr(scrape, "parse_job_description", fake_parse_job_description)

    result = asyncio.run(
        scrape.scrape_analyze(
            ScrapeAnalyzeRequest(text=job_url),
            db=object(),
            client=object(),
        )
    )

    assert scraped_urls == [job_url]
    assert result.company_name == "Appier"
    assert result.role_title == "AI Engineer, Playable Ads - Tokyo Japan."
    assert result.location == "Tokyo, Japan"
    assert result.source == "greenhouse_api"
