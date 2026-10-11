import asyncio

from app.routes import scrape
from app.schemas import ParseJobDescriptionResponse, ScrapeAnalyzeRequest
from app.services.scraper import ScrapedJob


def test_structured_salary_is_added_without_losing_posted_salary_text(monkeypatch):
    async def fake_scrape_job_url(url: str, client) -> ScrapedJob:
        return ScrapedJob(
            job_description="Senior Engineer. Competitive compensation.",
            company_name="Acme",
            role_title="Senior Engineer",
            location="Remote",
            salary="Competitive",
            source="greenhouse_api",
        )

    def fake_parse_job_description(*args, **kwargs) -> ParseJobDescriptionResponse:
        return ParseJobDescriptionResponse(
            company_name="Acme",
            role_title="Senior Engineer",
            location="Remote",
            salary="$140,000 - $170,000 per year",
            min_salary=140000,
            max_salary=170000,
        )

    monkeypatch.setattr(scrape, "require_llm_config", lambda db: ("openai", "secret"))
    monkeypatch.setattr(scrape, "scrape_job_url", fake_scrape_job_url)
    monkeypatch.setattr(scrape, "parse_job_description", fake_parse_job_description)

    result = asyncio.run(
        scrape.scrape_analyze(
            ScrapeAnalyzeRequest(url="https://job-boards.greenhouse.io/acme/jobs/1"),
            db=object(),
            client=object(),
        )
    )

    assert result.salary == "Competitive"
    assert result.min_salary == 140000
    assert result.max_salary == 170000


def test_structured_salary_defaults_to_none_when_not_extracted(monkeypatch):
    def fake_parse_job_description(*args, **kwargs) -> ParseJobDescriptionResponse:
        return ParseJobDescriptionResponse(
            company_name=None,
            role_title=None,
            location=None,
            salary="Hourly pay, amount not specified",
        )

    monkeypatch.setattr(scrape, "require_llm_config", lambda db: ("openai", "secret"))
    monkeypatch.setattr(scrape, "parse_job_description", fake_parse_job_description)

    result = asyncio.run(
        scrape.scrape_analyze(
            ScrapeAnalyzeRequest(text="Hourly pay, amount not specified."),
            db=object(),
            client=object(),
        )
    )

    assert result.min_salary is None
    assert result.max_salary is None
