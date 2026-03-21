import re
from dataclasses import dataclass
from typing import Literal

import httpx

CHALLENGE_SIGNALS = [
    "access denied",
    "just a moment",
    "enable javascript",
    "checking your browser",
    "cf-browser-verification",
]


@dataclass
class ScrapedJob:
    job_description: str
    company_name: str | None
    role_title: str | None
    location: str | None
    salary: str | None
    source: Literal["greenhouse_api", "lever_api", "ashby_api", "jina", "crawl4ai"]


def _is_challenge_page(text: str) -> bool:
    if len(text) < 200:
        return True
    lower = text.lower()
    return any(signal in lower for signal in CHALLENGE_SIGNALS)


def _detect_ats(url: str) -> str:
    if "greenhouse.io" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "ashbyhq.com" in url:
        return "ashby"
    if "jazzhr.com" in url:
        return "jazzhr"
    if "bamboohr.com" in url:
        return "bamboohr"
    return "generic"


def _scrape_greenhouse(url: str) -> ScrapedJob:
    """Extract job ID and company token from Greenhouse URL, hit public API."""
    # Handles: boards.greenhouse.io/company/jobs/12345
    #          boards-api.greenhouse.io/v1/boards/company/jobs/12345
    match = re.search(r"greenhouse\.io/(?:v\d/boards/)?([^/]+)/jobs/(\d+)", url)
    if not match:
        raise ValueError("Could not parse Greenhouse URL")
    company, job_id = match.group(1), match.group(2)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"
    r = httpx.get(api_url, timeout=10)
    r.raise_for_status()
    data = r.json()
    content = re.sub(r"<[^>]+>", " ", data.get("content", ""))
    content = re.sub(r"\s+", " ", content).strip()
    title = data.get("title", "")
    dept = (
        data.get("departments", [{}])[0].get("name", "")
        if data.get("departments")
        else ""
    )
    location = (
        data.get("location", {}).get("name", None)
        if isinstance(data.get("location"), dict)
        else data.get("location")
    )
    jd = f"{title}\n{dept}\n\n{content}".strip()
    return ScrapedJob(
        job_description=jd,
        company_name=company.replace("-", " ").title(),
        role_title=title,
        location=location,
        salary=None,
        source="greenhouse_api",
    )


def _scrape_lever(url: str) -> ScrapedJob:
    """Extract posting ID from Lever URL, hit public API."""
    # Handles: jobs.lever.co/company/uuid
    match = re.search(r"lever\.co/([^/]+)/([a-f0-9-]+)", url)
    if not match:
        raise ValueError("Could not parse Lever URL")
    company, posting_id = match.group(1), match.group(2)
    api_url = f"https://api.lever.co/v0/postings/{company}/{posting_id}"
    r = httpx.get(api_url, timeout=10)
    r.raise_for_status()
    data = r.json()
    lists = data.get("lists", [])
    description = data.get("descriptionPlain", "") or data.get("description", "")
    description = re.sub(r"<[^>]+>", " ", description)
    details = "\n".join(
        f"{lst['text']}:\n" + "\n".join(f"- {item}" for item in lst.get("content", []))
        for lst in lists
    )
    jd = f"{data.get('text', '')}\n\n{description}\n\n{details}".strip()
    return ScrapedJob(
        job_description=jd,
        company_name=company.replace("-", " ").title(),
        role_title=data.get("text", ""),
        location=data.get("location"),
        salary=None,
        source="lever_api",
    )


def _scrape_ashby(url: str) -> ScrapedJob:
    """Extract job info from Ashby URL using their public API."""
    # Handles: ashbyhq.com/jobs/{jobId}
    #          ashbyhq.com/{company}/jobs/{jobId}
    # Ashby API: https://api.ashbyhq.com/v2/{companyName}/jobs/{jobId}
    match = re.search(r"ashbyhq\.com/(?:careers/)?([^/]+)/jobs/([a-f0-9-]+)", url)
    if not match:
        raise ValueError("Could not parse Ashby URL")
    company, job_id = match.group(1), match.group(2)
    # If company is "jobs" or "careers", we can't determine company name from URL
    if company in ("jobs", "careers"):
        raise ValueError("Could not determine Ashby company name from URL")
    api_url = f"https://api.ashbyhq.com/v2/{company}/jobs/{job_id}"
    r = httpx.get(api_url, timeout=10)
    r.raise_for_status()
    data = r.json()
    job_data = data.get("job", {})
    content = job_data.get("description", "") or job_data.get("body", "")
    content = re.sub(r"<[^>]+>", " ", content)
    content = re.sub(r"\s+", " ", content).strip()
    title = job_data.get("title", "")
    location = job_data.get("location", "")
    jd = f"{title}\n\n{content}".strip()
    return ScrapedJob(
        job_description=jd,
        company_name=company.replace("-", " ").title(),
        role_title=title,
        location=location,
        salary=None,
        source="ashby_api",
    )


async def _scrape_jina(url: str) -> str | None:
    """Try Jina Reader; return markdown or None on challenge/failure."""
    jina_url = f"https://r.jina.ai/{url}"
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(jina_url)
            text = r.text
            if _is_challenge_page(text):
                return None
            return text
        except Exception:
            return None


async def _scrape_crawl4ai(url: str) -> str | None:
    """Try Crawl4AI with stealth mode; return markdown or None on failure."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        async with AsyncWebCrawler(
            config=BrowserConfig(enable_stealth=True)
        ) as crawler:
            result = await crawler.arun(url=url, config=CrawlerRunConfig(magic=True))
            return result.markdown or None
    except Exception:
        return None


async def scrape_job_url(url: str, provider: str = "auto") -> ScrapedJob:
    """
    Tiered scraper:
    1. Greenhouse/Lever/Ashby JSON API (httpx, no browser)
    2. Jina Reader (free managed)
    3. Crawl4AI (local Playwright stealth)
    4. Raise ValueError if all fail
    """
    ats = _detect_ats(url)

    if ats == "greenhouse":
        return _scrape_greenhouse(url)

    if ats == "lever":
        return _scrape_lever(url)

    if ats == "ashby":
        return _scrape_ashby(url)

    # Tier 2: Jina
    jina_result = await _scrape_jina(url)
    if jina_result:
        return ScrapedJob(
            job_description=jina_result,
            company_name=None,
            role_title=None,
            location=None,
            salary=None,
            source="jina",
        )

    # Tier 3: Crawl4AI
    crawl_result = await _scrape_crawl4ai(url)
    if crawl_result:
        return ScrapedJob(
            job_description=crawl_result,
            company_name=None,
            role_title=None,
            location=None,
            salary=None,
            source="crawl4ai",
        )

    raise ValueError("Could not extract job posting. Please paste the text manually.")
