# Job Posting URL Scraping — Research

**Date:** 2026-03-16
**Context:** Research for ApplyKit's "Smart URL Cover Letter Generator" — user pastes a job posting URL, the app extracts the job description and feeds it to the LLM to generate a tailored cover letter.

---

## The Core Problem

Job boards split into two categories requiring different approaches:

| Category | Examples | Challenge |
|----------|----------|-----------|
| **Easy ATS** | Greenhouse, Lever, Ashby | Public JSON APIs — no scraping needed |
| **Hard platforms** | LinkedIn, Indeed, Workday | JS rendering + Cloudflare + DataDome + active bot detection |

---

## Option 1: Firecrawl

**Type:** Managed cloud SaaS (closed-source)
**URL:** https://www.firecrawl.dev

**Cost:**
- Free trial: 500 credits, one-time only (not recurring)
- Hobby: $16/month (3,000 pages/mo)
- Standard: $83/month (100,000 pages/mo)

**JS Rendering:** Yes — managed proxies, anti-bot, JS rendering in the cloud

**Python Integration:**
```python
from firecrawl import Firecrawl
app = Firecrawl(api_key="fc-YOUR-KEY")
result = app.scrape("https://example.com/job/123")
```

**Pros:**
- Zero infrastructure — one SDK call
- Handles most ATS pages well
- Clean markdown output ready for LLM

**Cons:**
- No free recurring tier — effectively paid from day one
- LinkedIn actively blocks Firecrawl
- Known failures on DataDome/PerimeterX protected pages
- Vendor lock-in — if they raise prices or shut down, you're stuck

**Verdict:** Good for Greenhouse/Lever/Workday ATS pages. Unreliable for LinkedIn. Not ideal for a self-hosted app trying to minimize costs.

---

## Option 2: Jina Reader

**Type:** Managed cloud API — genuinely free tier
**URL:** https://r.jina.ai

**Cost:**
- No API key: 20 RPM (free, slow)
- Free API key: 500 RPM, 10M tokens free grant

**JS Rendering:** Yes — renders in a browser proxy before returning Markdown

**Python Integration:**
```python
import httpx
response = httpx.get(
    f"https://r.jina.ai/{job_url}",
    headers={"Authorization": "Bearer YOUR_KEY"}
)
markdown = response.text
```

**Pros:**
- Genuinely free for low-volume self-hosted use
- Zero infrastructure — single HTTP call
- No SDK dependency
- Returns clean Markdown immediately

**Cons:**
- Does NOT bypass anti-bot protections (their own docs state this explicitly)
- LinkedIn, Cloudflare-protected Indeed, and Workday will fail silently
- Returns challenge page HTML instead of job content on blocked sites

**Verdict:** Best free option for open ATS pages. Falls back gracefully. Good first-try before more expensive approaches.

---

## Option 3: Crawl4AI (Recommended for Self-Hosted)

**Type:** Open-source Python library (MIT license)
**URL:** https://docs.crawl4ai.com
**GitHub:** https://github.com/unclecode/crawl4ai

**Cost:** Free — runs locally

**JS Rendering:** Yes — built on Playwright internally

**Python Integration:**
```python
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async with AsyncWebCrawler(config=BrowserConfig(enable_stealth=True)) as crawler:
    result = await crawler.arun(
        url=job_url,
        config=CrawlerRunConfig(magic=True)
    )
    return result.markdown
```

**Anti-Bot Features:**
- `enable_stealth=True` — patches navigator.webdriver fingerprints
- `use_undetected_browser=True` — heavier Cloudflare/DataDome bypass
- `magic=True` — adaptive crawling mode
- Built-in proxy rotation with escalation chain

**Pros:**
- Free, self-hosted, no per-request cost
- Best anti-bot capability of all self-hosted options
- Handles Greenhouse/Lever trivially
- Works on many Indeed pages with stealth mode
- Full control over behavior

**Cons:**
- Requires Playwright/Chromium (~200-400MB in Docker)
- LinkedIn still requires residential proxies at volume
- Async-first — needs careful integration in FastAPI

**Installation:**
```bash
uv add crawl4ai
crawl4ai-setup  # installs Playwright browsers
```

**Verdict:** Best self-hosted option. Recommended as the primary scraper for non-trivial pages.

---

## Option 4: BeautifulSoup + httpx (DIY Static)

**Type:** Open-source Python libraries
**Cost:** Free

**JS Rendering:** No — pure HTTP requests only

**Best use case:** Greenhouse and Lever have public JSON APIs — no scraping at all needed:

```python
import httpx

# Greenhouse
r = httpx.get("https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{id}")
job = r.json()

# Lever
r = httpx.get("https://api.lever.co/v0/postings/{company}/{id}")
job = r.json()
```

**Pros:** Zero dependencies beyond httpx, instant, reliable
**Cons:** Useless for JS-rendered pages

**Verdict:** Use for Greenhouse/Lever URL detection as Tier 1. Not viable for anything else.

---

## Option 5: Playwright (Headless Browser DIY)

**Type:** Open-source (Microsoft)
**Cost:** Free

**JS Rendering:** Yes — full Chromium/Firefox/WebKit

**Anti-Bot Hardening:**
- `playwright-stealth` — patches common detection signals
- **Patchright** (`pip install patchright`) — patched Playwright that fixes CDP leaks, currently considered the most effective undetected option

**Best for:** Workday (intercept internal JSON API calls via `page.on("response", ...)`)

**Pros:** Maximum control, handles Workday best
**Cons:** Highest implementation effort, ~400MB Chromium binary, LinkedIn still needs proxies

**Verdict:** Use for Workday specifically if needed. Crawl4AI wraps Playwright anyway — prefer Crawl4AI.

---

## Option 6: JobOps (Community Alternative)

**Type:** Open-source TypeScript, self-hosted Docker
**URL:** https://github.com/DaKheera47/job-ops

**What it does:** Full job-hunt automation — scrapes job boards by search criteria (not single URL), AI-scores fit, tailors resumes via RxResume, tracks Gmail responses.

**Platforms:** LinkedIn, Indeed, Glassdoor, Adzuna, Hiring Café, Gradcracker, UK Visa Jobs

**Stack:** TypeScript, Next.js, SQLite, Docker, multi-LLM (OpenAI/Gemini/Ollama)

**Relevance to ApplyKit:**
- JobOps is a **search-based** scraper (find jobs by keyword/location) — not URL-based (paste a specific posting URL)
- Could integrate as inspiration for the extractor architecture
- TypeScript — not directly usable in FastAPI Python backend
- The extractor system could be studied for platform-specific parsing logic

**Pros:** Full platform coverage, proven scraping for LinkedIn/Indeed, MIT open source
**Cons:** TypeScript only, search-oriented not URL-oriented, heavy stack (full Docker deployment)

---

## Recommended Architecture for ApplyKit

Use a tiered fallback approach:

```
User pastes job URL
        │
        ▼
Tier 1: Is it Greenhouse or Lever?
        │ Yes → Hit their public JSON API directly (httpx, no scraping)
        │ No ↓
        ▼
Tier 2: Try Jina Reader (free, zero infrastructure)
        │ Success → Use markdown
        │ Fail (empty/challenge page) ↓
        ▼
Tier 3: Try Crawl4AI with stealth mode (self-hosted)
        │ Success → Use markdown
        │ Fail (LinkedIn, hard blocks) ↓
        ▼
Tier 4: Return friendly error
        "This job board is heavily protected. Please paste the job description text directly."
```

### URL Detection Logic

```python
def detect_ats(url: str) -> str:
    if "greenhouse.io" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "linkedin.com" in url:
        return "linkedin"  # warn user
    return "generic"
```

### LinkedIn Reality Check

LinkedIn actively blocks all scrapers. Options:
- Residential proxies ($10-50/mo) — required for reliable LinkedIn scraping
- Accept the limitation and show: *"LinkedIn URLs are not reliably supported — paste the job description text instead"*
- For a self-hosted app, the manual paste fallback is the pragmatic choice

---

## Summary Table

| Solution | Cost | JS Pages | LinkedIn | Indeed | Greenhouse/Lever | Self-Hosted |
|----------|------|----------|----------|--------|-----------------|-------------|
| Firecrawl | $16+/mo | ✅ | ❌ blocked | ⚠️ partial | ✅ | ❌ |
| Jina Reader | Free | ✅ | ❌ | ❌ Cloudflare | ✅ | ❌ |
| **Crawl4AI** | **Free** | **✅** | **⚠️ needs proxy** | **✅ stealth** | **✅** | **✅** |
| BS4 + httpx | Free | ❌ | ❌ | ❌ | ✅ (JSON API) | ✅ |
| Playwright | Free | ✅ | ⚠️ needs proxy | ✅ Patchright | ✅ | ✅ |
| JobOps | Free | ✅ | ✅ | ✅ | ✅ | ✅ (Docker) |

**Final recommendation:** Tier 1 (JSON APIs) + Tier 2 (Jina) + Tier 3 (Crawl4AI) + manual paste fallback. Zero ongoing cost, covers ~80% of real-world job posting URLs.
