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


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


async def _scrape_greenhouse(url: str, client: httpx.AsyncClient) -> ScrapedJob:
    """Extract job ID and company token from Greenhouse URL, hit public API."""
    match = re.search(r"greenhouse\.io/(?:v\d/boards/)?([^/]+)/jobs/(\d+)", url)
    if not match:
        raise ValueError("Could not parse Greenhouse URL")
    company, job_id = match.group(1), match.group(2)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"

    r = await client.get(api_url, timeout=10)
    r.raise_for_status()
    data = r.json()

    content = _strip_html(data.get("content", ""))
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


async def _scrape_lever(url: str, client: httpx.AsyncClient) -> ScrapedJob:
    """Extract posting ID from Lever URL, hit public API."""
    match = re.search(r"lever\.co/([^/]+)/([a-f0-9-]+)", url)
    if not match:
        raise ValueError("Could not parse Lever URL")
    company, posting_id = match.group(1), match.group(2)
    api_url = f"https://api.lever.co/v0/postings/{company}/{posting_id}"

    r = await client.get(api_url, timeout=10)
    r.raise_for_status()
    data = r.json()

    lists = data.get("lists", [])
    description = data.get("descriptionPlain", "") or data.get("description", "")
    description = _strip_html(description)
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


async def _scrape_ashby(url: str, client: httpx.AsyncClient) -> ScrapedJob:
    """Extract job info from Ashby URL using their public API."""
    match = re.search(r"ashbyhq\.com/(?:careers/)?([^/]+)/jobs/([a-f0-9-]+)", url)
    if not match:
        raise ValueError("Could not parse Ashby URL")
    company, job_id = match.group(1), match.group(2)
    if company in ("jobs", "careers"):
        raise ValueError("Could not determine Ashby company name from URL")
    api_url = f"https://api.ashbyhq.com/v2/{company}/jobs/{job_id}"

    r = await client.get(api_url, timeout=10)
    r.raise_for_status()
    data = r.json()

    job_data = data.get("job", {})
    content = _strip_html(job_data.get("description", "") or job_data.get("body", ""))
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


async def _scrape_jina(url: str, client: httpx.AsyncClient) -> str | None:
    """Try Jina Reader; return markdown or None on challenge/failure."""
    jina_url = f"https://r.jina.ai/{url}"
    try:
        r = await client.get(jina_url, timeout=15)
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


async def scrape_job_url(
    url: str, client: httpx.AsyncClient, provider: str = "auto"
) -> ScrapedJob:
    """
    Tiered scraper:
    1. Greenhouse/Lever/Ashby JSON API (shared async httpx client)
    2. Jina Reader (shared client)
    3. Crawl4AI (local Playwright stealth — uses its own browser)
    4. Raise ValueError if all fail
    """
    ats = _detect_ats(url)

    if ats == "greenhouse":
        return await _scrape_greenhouse(url, client)

    if ats == "lever":
        return await _scrape_lever(url, client)

    if ats == "ashby":
        return await _scrape_ashby(url, client)

    # Tier 2: Jina
    jina_result = await _scrape_jina(url, client)
    if jina_result:
        return ScrapedJob(
            job_description=jina_result,
            company_name=None,
            role_title=None,
            location=None,
            salary=None,
            source="jina",
        )

    # Tier 3: Crawl4AI (uses its own Playwright browser, not httpx)
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
