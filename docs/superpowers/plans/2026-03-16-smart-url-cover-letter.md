# Smart URL Cover Letter Generator Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add URL-based job import, AI fit analysis, streaming cover letter generation with tone selector, and a server-side filtered history UX with application status tags and bulk delete.

**Architecture:** Tiered scraper service (Greenhouse/Lever JSON APIs → Jina Reader → Crawl4AI), fit analysis LLM service, streaming SSE via `litellm.acompletion`, new DB columns on `generated_cover_letter` and `generated_cv`, history endpoints extended with server-side filtering.

**Tech Stack:** FastAPI, litellm (streaming), Crawl4AI + Playwright, httpx, SQLAlchemy, Alembic, SvelteKit (Svelte 5 runes), Tailwind CSS 4

---

## Chunk 1: Backend — Scraper + Fit Analysis Services

### Task 1: Install Dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add crawl4ai**

```bash
cd backend
uv add crawl4ai
```

Expected: `crawl4ai` added to `pyproject.toml` dependencies.

- [ ] **Step 2: Install Playwright browsers (required by crawl4ai)**

```bash
cd backend
uv run crawl4ai-setup
```

Expected: Playwright/Chromium downloaded (~300MB). Takes 1-2 minutes.

- [ ] **Step 3: Commit**

```bash
rtk git add backend/pyproject.toml backend/uv.lock
rtk git commit -m "chore: add crawl4ai dependency"
```

---

### Task 2: Scraper Service

**Files:**
- Create: `backend/app/services/scraper.py`

- [ ] **Step 1: Create the scraper service**

```python
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
    source: Literal["greenhouse_api", "lever_api", "jina", "crawl4ai"]


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
    # Strip HTML tags from content
    content = re.sub(r"<[^>]+>", " ", data.get("content", ""))
    content = re.sub(r"\s+", " ", content).strip()
    title = data.get("title", "")
    dept = data.get("departments", [{}])[0].get("name", "") if data.get("departments") else ""
    jd = f"{title}\n{dept}\n\n{content}".strip()
    return ScrapedJob(
        job_description=jd,
        company_name=company.replace("-", " ").title(),
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
        source="lever_api",
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

        async with AsyncWebCrawler(config=BrowserConfig(enable_stealth=True)) as crawler:
            result = await crawler.arun(url=url, config=CrawlerRunConfig(magic=True))
            return result.markdown or None
    except Exception:
        return None


async def scrape_job_url(url: str, provider: str = "auto") -> ScrapedJob:
    """
    Tiered scraper:
    1. Greenhouse/Lever JSON API (httpx, no browser)
    2. Jina Reader (free managed)
    3. Crawl4AI (local Playwright stealth)
    4. Raise ValueError if all fail
    """
    ats = _detect_ats(url)

    if ats == "greenhouse":
        return _scrape_greenhouse(url)

    if ats == "lever":
        return _scrape_lever(url)

    # Tier 2: Jina
    jina_result = await _scrape_jina(url)
    if jina_result:
        return ScrapedJob(job_description=jina_result, company_name=None, source="jina")

    # Tier 3: Crawl4AI
    crawl_result = await _scrape_crawl4ai(url)
    if crawl_result:
        return ScrapedJob(job_description=crawl_result, company_name=None, source="crawl4ai")

    raise ValueError(
        "Could not extract job posting. Please paste the text manually."
    )
```

- [ ] **Step 2: Commit**

```bash
rtk git add backend/app/services/scraper.py
rtk git commit -m "feat: add tiered job URL scraper service"
```

---

### Task 3: Scrape Route

**Files:**
- Create: `backend/app/routes/scrape.py`

- [ ] **Step 1: Create the route**

```python
from fastapi import APIRouter, HTTPException

from app.schemas import ScrapeJobRequest, ScrapeJobResponse
from app.services.scraper import scrape_job_url

router = APIRouter()


@router.post("/scrape/job", response_model=ScrapeJobResponse)
async def scrape_job(body: ScrapeJobRequest):
    try:
        result = await scrape_job_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail="Could not extract job posting. Please paste the text manually.",
        )
    return ScrapeJobResponse(
        job_description=result.job_description,
        company_name=result.company_name,
        source=result.source,
    )
```

- [ ] **Step 2: Add schemas to `schemas.py`** _(complete this before writing the route file)_

```python
# --- Scraper schemas ---

class ScrapeJobRequest(BaseModel):
    url: str

class ScrapeJobResponse(BaseModel):
    job_description: str
    company_name: str | None
    source: Literal["greenhouse_api", "lever_api", "jina", "crawl4ai"]
```

- [ ] **Step 3: Register in `main.py`**

Add `scrape` to the import line:
```python
from app.routes import generate, history, import_cv, profile, profiles, scrape, settings
```

Add after existing routers:
```python
app.include_router(scrape.router, prefix="/api")
```

- [ ] **Step 4: Commit**

```bash
rtk git add backend/app/routes/scrape.py backend/app/schemas.py backend/main.py
rtk git commit -m "feat: add scrape job URL route"
```

---

### Task 4: Fit Analysis Service

**Files:**
- Create: `backend/app/services/fit_analysis.py`

- [ ] **Step 1: Create the fit analysis service**

```python
import json

from app.schemas import FitAnalysisResponse
from app.services.llm import call_llm

FIT_SYSTEM_PROMPT = """\
You are a career coach analyzing a candidate's fit for a job.
Return ONLY valid JSON with exactly these keys:
match_score (integer 0-100),
pros (array of strings — profile strengths matching the role),
cons (array of strings — gaps or weaknesses),
missing_keywords (array of strings — keywords in JD not present in profile),
red_flags (array of strings — hard blockers like years required; empty array if none),
suggested_emphasis (string — one paragraph advising what to emphasize in the cover letter),
interview_questions (array of 3 strings — likely questions based on gaps).
No markdown, no explanation — just the raw JSON object."""


def analyze_fit(
    profile_json: str,
    job_description: str,
    provider: str,
    api_key: str,
) -> FitAnalysisResponse:
    user_prompt = (
        f"Profile:\n{profile_json}\n\n"
        f"Job Description:\n{job_description}\n\n"
        "Analyze fit and return JSON."
    )
    raw = call_llm(user_prompt, system=FIT_SYSTEM_PROMPT, provider=provider, api_key=api_key, timeout=30)
    cleaned = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    data = json.loads(cleaned)
    return FitAnalysisResponse(**data)
```

- [ ] **Step 2: Add schemas to `schemas.py`**

```python
# --- Fit analysis schemas ---

class FitAnalysisRequest(BaseModel):
    profile_id: int
    job_description: str

class FitAnalysisResponse(BaseModel):
    match_score: int
    pros: list[str]
    cons: list[str]
    missing_keywords: list[str]
    red_flags: list[str]
    suggested_emphasis: str
    interview_questions: list[str]
```

- [ ] **Step 3: Commit**

```bash
rtk git add backend/app/services/fit_analysis.py backend/app/schemas.py
rtk git commit -m "feat: add fit analysis LLM service"
```

---

### Task 5: Fit Analysis Route

**Files:**
- Modify: `backend/app/utils.py`
- Modify: `backend/app/routes/generate.py`
- Create: `backend/app/routes/analyze.py`

- [ ] **Step 1: Move `_format_profile_for_llm` to `utils.py`**

`_format_profile_for_llm` is currently a private function in `generate.py`. Both `generate.py` and the new `analyze.py` need it, so move it to `utils.py` as a public function.

In `backend/app/utils.py`, add at the bottom (requires `from app.schemas import ProfileData` — already imported via `profile_to_schema`):

```python
def format_profile_for_llm(p: ProfileData) -> str:
    """Format a ProfileData object as a structured text block for LLM prompts."""
    lines = []
    if p.name:
        lines.append(f"NAME: {p.name}")
    if p.email:
        lines.append(f"EMAIL: {p.email}")
    if p.phone:
        lines.append(f"PHONE: {p.phone}")
    if p.location:
        lines.append(f"LOCATION: {p.location}")
    if p.linkedin:
        lines.append(f"LINKEDIN: {p.linkedin}")
    if p.github:
        lines.append(f"GITHUB: {p.github}")
    if p.portfolio:
        lines.append(f"PORTFOLIO: {p.portfolio}")
    if p.summary:
        lines.append(f"\nSUMMARY:\n{p.summary}")
    if p.work_experience:
        lines.append("\nWORK EXPERIENCE:")
        for job in p.work_experience:
            lines.append(
                f"  {job.get('title', '')} at {job.get('company', '')} "
                f"({job.get('start_date', '')} – {job.get('end_date', 'Present')})"
            )
            if job.get("description"):
                lines.append(f"    {job['description']}")
    if p.education:
        lines.append("\nEDUCATION:")
        for edu in p.education:
            lines.append(
                f"  {edu.get('degree', '')} from {edu.get('institution', '')} "
                f"({edu.get('year', '')})"
            )
    if p.skills:
        lines.append(f"\nSKILLS: {', '.join(str(s) for s in p.skills)}")
    if p.projects:
        lines.append("\nPROJECTS:")
        for proj in p.projects:
            lines.append(f"  {proj.get('name', '')}: {proj.get('description', '')}")
    if p.certifications:
        lines.append("\nCERTIFICATIONS:")
        for cert in p.certifications:
            lines.append(f"  {cert.get('name', '')} ({cert.get('year', '')})")
    return "\n".join(lines)
```

Then in `backend/app/routes/generate.py`, replace the private function with an import:

Find the existing `def _format_profile_for_llm(p: ProfileData) -> str:` function and replace it with:

```python
from app.utils import format_profile_for_llm as _format_profile_for_llm
```

- [ ] **Step 2: Create the route**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import FitAnalysisRequest, FitAnalysisResponse
from app.services.fit_analysis import analyze_fit
from app.services.llm import APIKeyNotConfiguredError, LLMCallError
from app.services.settings import get_llm_config
from app.utils import format_profile_for_llm, profile_to_schema

router = APIRouter()


@router.post("/analyze/fit", response_model=FitAnalysisResponse)
def analyze_fit_endpoint(body: FitAnalysisRequest, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter_by(id=body.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    provider, api_key = get_llm_config(db)
    profile_data = profile_to_schema(profile)
    profile_json = format_profile_for_llm(profile_data)

    try:
        return analyze_fit(profile_json, body.job_description, provider, api_key)
    except APIKeyNotConfiguredError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMCallError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fit analysis failed: {e}")
```

- [ ] **Step 3: Register in `main.py`**

Add `analyze` to the import line and include the router:
```python
from app.routes import analyze, generate, history, import_cv, profile, profiles, scrape, settings
```
```python
app.include_router(analyze.router, prefix="/api")
```

- [ ] **Step 4: Commit**

```bash
rtk git add backend/app/utils.py backend/app/routes/generate.py backend/app/routes/analyze.py backend/main.py
rtk git commit -m "feat: add analyze fit route, move format_profile_for_llm to utils"
```

---

## Chunk 2: Backend — Cover Letter Revamp + History Overhaul

### Task 6: DB Migration — New Columns

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/migrations/versions/<hash>_smart_url_cover_letter.py`

- [ ] **Step 1: Add new columns to models**

In `GeneratedCoverLetter`, add after `profile_id`:

```python
job_url = Column(String, nullable=True)
match_score = Column(Integer, nullable=True)
fit_analysis = Column(Text, nullable=True)     # JSON string of FitAnalysisResponse
tone = Column(String, nullable=False, default="professional")
application_status = Column(String, nullable=True, default=None)
```

In `GeneratedCV`, add after `profile_id`:

```python
application_status = Column(String, nullable=True, default=None)
```

- [ ] **Step 2: Generate and apply migration**

```bash
cd backend
uv run alembic revision --autogenerate -m "smart_url_cover_letter_columns"
uv run alembic upgrade head
```

Verify the generated migration adds all 5 new columns to `generated_cover_letter` and 1 column to `generated_cv`.

- [ ] **Step 3: Commit**

```bash
rtk git add backend/app/models.py backend/migrations/
rtk git commit -m "feat: add smart URL cover letter columns to DB"
```

---

### Task 7: Schema Updates — Cover Letter + History

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Extend `CoverLetterRequest` with new fields**

```python
class CoverLetterRequest(BaseModel):
    profile_id: int
    job_description: str
    company_name: str | None = None
    extra_context: str = ""
    tone: Literal["professional", "enthusiastic", "concise", "creative"] = "professional"
    job_url: str | None = None
    fit_context: str | None = None
    match_score: int | None = None          # from fit analysis — persisted to generated_cover_letter
    fit_analysis_json: str | None = None    # JSON string of FitAnalysisResponse — persisted to generated_cover_letter.fit_analysis
```

- [ ] **Step 2: Update `CoverLetterResponse`**

```python
class CoverLetterResponse(BaseModel):
    cover_letter_text: str
```

- [ ] **Step 3: Update `GeneratedCoverLetterEntry` and list response**

```python
class GeneratedCoverLetterEntry(BaseModel):
    id: int
    created_at: datetime
    company_name: str | None
    job_description: str
    extra_context: str | None
    cover_letter_text: str
    tone: str
    job_url: str | None
    match_score: int | None
    fit_analysis: dict | None
    application_status: str | None
    profile_id: int | None = None
    profile_label: str | None = None
    profile_color: str | None = None
    profile_icon: str | None = None

    model_config = {"from_attributes": True}


class GeneratedCoverLetterListResponse(BaseModel):
    items: list[GeneratedCoverLetterEntry]
    total: int
```

- [ ] **Step 4: Update `GeneratedCVEntry` and list response**

```python
class GeneratedCVEntry(BaseModel):
    id: int
    created_at: datetime
    enhanced: bool
    profile_snapshot: str
    application_status: str | None
    profile_id: int | None = None
    profile_label: str | None = None
    profile_color: str | None = None
    profile_icon: str | None = None

    model_config = {"from_attributes": True}


class GeneratedCVListResponse(BaseModel):
    items: list[GeneratedCVEntry]
    total: int
```

- [ ] **Step 5: Add history status + bulk delete schemas**

```python
class UpdateStatusRequest(BaseModel):
    status: str | None  # None clears status back to null

class BulkDeleteRequest(BaseModel):
    ids: list[int]
```

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/schemas.py
rtk git commit -m "feat: update cover letter and history schemas for smart URL feature"
```

---

### Task 8: Streaming Cover Letter Generation

**Files:**
- Modify: `backend/app/services/llm.py`
- Modify: `backend/app/routes/generate.py`

- [ ] **Step 1: Add `stream_llm` async generator to `llm.py`**

```python
from typing import AsyncGenerator

async def stream_llm(
    prompt: str,
    system: str | None = None,
    provider: str = "",
    api_key: str = "",
) -> AsyncGenerator[str, None]:
    if not provider or not api_key:
        raise APIKeyNotConfiguredError(
            "LLM not configured. Set provider and API key in Settings."
        )
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        response = await litellm.acompletion(
            model=provider,
            messages=messages,
            api_key=api_key,
            stream=True,
            timeout=60,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
    except (APIKeyNotConfiguredError, LLMCallError):
        raise
    except Exception as e:
        raise LLMCallError(str(e)) from e
```

- [ ] **Step 2: Add tone prompts dict and update `_build_cover_letter_prompt` in `generate.py`**

At the top of `generate.py`, add:

```python
from fastapi.responses import StreamingResponse

TONE_PROMPTS = {
    "professional": "Write in a formal, polished tone.",
    "enthusiastic": "Write in an energetic, passionate tone that conveys genuine excitement.",
    "concise": "Write concisely — aim for under 200 words. No filler.",
    "creative": "Write in a distinctive, memorable style that stands out.",
}
```

Update `_build_cover_letter_prompt` to inject tone and fit_context:

```python
def _build_cover_letter_prompt(p: ProfileData, req: CoverLetterRequest) -> str:
    parts = [_format_profile_for_llm(p)]
    parts.append(f"\n---\nJOB DESCRIPTION:\n{req.job_description}")
    if req.company_name:
        parts.append(f"\nCOMPANY NAME: {req.company_name}")
    if req.extra_context and req.extra_context.strip():
        parts.append(
            f"\nSPECIAL INSTRUCTIONS FROM CANDIDATE:\n{req.extra_context.strip()}"
        )
    if req.fit_context and req.fit_context.strip():
        parts.append(
            f"\nAdditional context from the candidate: {req.fit_context.strip()}.\n"
            "Use this to guide emphasis — do not fabricate experience, but frame existing "
            "experience to address these points where honest."
        )
    tone_modifier = TONE_PROMPTS.get(req.tone or "professional", TONE_PROMPTS["professional"])
    parts.append(f"\nTONE INSTRUCTION: {tone_modifier}")
    return "\n".join(parts)
```

- [ ] **Step 3: Replace `generate_cover_letter` endpoint with streaming version**

Replace the entire `@router.post("/generate/cover-letter", ...)` function:

```python
from app.services.llm import APIKeyNotConfiguredError, LLMCallError, call_llm, stream_llm


@router.post("/generate/cover-letter")
async def generate_cover_letter(req: CoverLetterRequest, db: Session = Depends(get_db)):
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)
    provider, api_key = get_llm_config(db)

    if not provider or not api_key:
        raise HTTPException(
            status_code=400,
            detail={"detail": "LLM not configured.", "code": "API_KEY_NOT_CONFIGURED"},
        )

    prompt = _build_cover_letter_prompt(profile_data, req)

    async def event_stream():
        accumulated = []
        try:
            async for chunk in stream_llm(prompt, system=COVER_LETTER_SYSTEM_PROMPT, provider=provider, api_key=api_key):
                accumulated.append(chunk)
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
            return

        # Per spec: yield [DONE] first, then DB write
        yield "data: [DONE]\n\n"

        full_text = "".join(accumulated)
        entry = GeneratedCoverLetter(
            company_name=req.company_name,
            job_description=req.job_description,
            extra_context=req.extra_context or None,
            cover_letter_text=full_text,
            profile_id=req.profile_id,
            job_url=req.job_url,
            tone=req.tone or "professional",
            match_score=req.match_score,
            fit_analysis=req.fit_analysis_json,
        )
        db.add(entry)
        db.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 4: Commit**

```bash
rtk git add backend/app/services/llm.py backend/app/routes/generate.py
rtk git commit -m "feat: streaming cover letter generation with tone + fit_context"
```

---

### Task 9: History Route Overhaul

**Files:**
- Modify: `backend/app/routes/history.py`

- [ ] **Step 1: Update `_enrich_cl` to include new fields**

```python
def _enrich_cl(entry: GeneratedCoverLetter, profiles: dict) -> dict:
    import json as _json
    p = profiles.get(entry.profile_id) if entry.profile_id else None
    fit = None
    raw_fit = getattr(entry, "fit_analysis", None)
    if raw_fit:
        try:
            fit = _json.loads(raw_fit)
        except Exception:
            fit = None
    return {
        "id": entry.id,
        "created_at": entry.created_at,
        "company_name": entry.company_name,
        "job_description": entry.job_description,
        "extra_context": entry.extra_context,
        "cover_letter_text": entry.cover_letter_text,
        "tone": getattr(entry, "tone", "professional"),
        "job_url": getattr(entry, "job_url", None),
        "match_score": getattr(entry, "match_score", None),
        "fit_analysis": fit,
        "application_status": getattr(entry, "application_status", None),
        "profile_id": entry.profile_id,
        "profile_label": p.label if p else None,
        "profile_color": p.color if p else None,
        "profile_icon": p.icon if p else None,
    }
```

- [ ] **Step 2: Update `_enrich_cv` to include `application_status`**

```python
def _enrich_cv(entry: GeneratedCV, profiles: dict) -> dict:
    p = profiles.get(entry.profile_id) if entry.profile_id else None
    return {
        "id": entry.id,
        "created_at": entry.created_at,
        "enhanced": bool(entry.enhanced),
        "profile_snapshot": entry.profile_snapshot,
        "application_status": getattr(entry, "application_status", None),
        "profile_id": entry.profile_id,
        "profile_label": p.label if p else None,
        "profile_color": p.color if p else None,
        "profile_icon": p.icon if p else None,
    }
```

- [ ] **Step 3: Update `list_cv_history` with pagination and sort**

```python
@router.get("/history/cv", response_model=GeneratedCVListResponse)
def list_cv_history(
    db: Session = Depends(get_db),
    profile_id: int | None = Query(default=None),
    sort: str = Query(default="date_desc"),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
):
    q = db.query(GeneratedCV)
    if profile_id is not None:
        q = q.filter(GeneratedCV.profile_id == profile_id)
    if sort == "date_asc":
        q = q.order_by(GeneratedCV.created_at.asc())
    else:
        q = q.order_by(GeneratedCV.created_at.desc())
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    pm = _profile_map(items, db)
    return GeneratedCVListResponse(items=[_enrich_cv(e, pm) for e in items], total=total)
```

- [ ] **Step 4: Update `list_cover_letter_history` with full server-side filtering**

```python
@router.get("/history/cover-letter", response_model=GeneratedCoverLetterListResponse)
def list_cover_letter_history(
    db: Session = Depends(get_db),
    profile_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    match_min: int | None = Query(default=None),
    match_max: int | None = Query(default=None),
    status: str | None = Query(default=None),
    sort: str = Query(default="date_desc"),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
):
    q = db.query(GeneratedCoverLetter)
    if profile_id is not None:
        q = q.filter(GeneratedCoverLetter.profile_id == profile_id)
    if search:
        term = f"%{search}%"
        q = q.filter(
            GeneratedCoverLetter.company_name.ilike(term)
            | GeneratedCoverLetter.job_description.ilike(term)
        )
    if match_min is not None:
        q = q.filter(GeneratedCoverLetter.match_score >= match_min)
    if match_max is not None:
        q = q.filter(GeneratedCoverLetter.match_score <= match_max)
    if status:
        q = q.filter(GeneratedCoverLetter.application_status == status)
    if sort == "date_asc":
        q = q.order_by(GeneratedCoverLetter.created_at.asc())
    elif sort == "match_desc":
        q = q.order_by(GeneratedCoverLetter.match_score.desc().nullslast())
    elif sort == "company_asc":
        q = q.order_by(GeneratedCoverLetter.company_name.asc().nullslast())
    else:
        q = q.order_by(GeneratedCoverLetter.created_at.desc())
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    pm = _profile_map(items, db)
    return GeneratedCoverLetterListResponse(
        items=[_enrich_cl(e, pm) for e in items], total=total
    )
```

- [ ] **Step 5: Add PATCH status endpoints**

```python
from app.schemas import BulkDeleteRequest, UpdateStatusRequest

@router.patch("/history/cover-letter/{entry_id}/status", response_model=GeneratedCoverLetterEntry)
def update_cover_letter_status(
    entry_id: int, body: UpdateStatusRequest, db: Session = Depends(get_db)
):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    entry.application_status = body.status
    db.commit()
    return _enrich_cl(entry, _profile_map([entry], db))


@router.patch("/history/cv/{entry_id}/status", response_model=GeneratedCVEntry)
def update_cv_status(
    entry_id: int, body: UpdateStatusRequest, db: Session = Depends(get_db)
):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    entry.application_status = body.status
    db.commit()
    return _enrich_cv(entry, _profile_map([entry], db))
```

- [ ] **Step 6: Add bulk delete endpoints**

```python
@router.delete("/history/cover-letter")
def bulk_delete_cover_letters(body: BulkDeleteRequest, db: Session = Depends(get_db)):
    deleted = (
        db.query(GeneratedCoverLetter)
        .filter(GeneratedCoverLetter.id.in_(body.ids))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted": deleted}


@router.delete("/history/cv")
def bulk_delete_cvs(body: BulkDeleteRequest, db: Session = Depends(get_db)):
    deleted = (
        db.query(GeneratedCV)
        .filter(GeneratedCV.id.in_(body.ids))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted": deleted}
```

- [ ] **Step 7: Commit**

```bash
rtk git add backend/app/routes/history.py backend/app/schemas.py
rtk git commit -m "feat: history route server-side filter, PATCH status, bulk delete"
```

---

## Chunk 3: Frontend

### Task 10: Types + API Updates

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add new types to `types.ts`**

```typescript
// Smart URL types
export interface ScrapeJobResponse {
  job_description: string;
  company_name: string | null;
  source: 'greenhouse_api' | 'lever_api' | 'jina' | 'crawl4ai';
}

export interface FitAnalysisResponse {
  match_score: number;
  pros: string[];
  cons: string[];
  missing_keywords: string[];
  red_flags: string[];
  suggested_emphasis: string;
  interview_questions: string[];
}

export type Tone = 'professional' | 'enthusiastic' | 'concise' | 'creative';
export type ApplicationStatus = 'applied' | 'interviewing' | 'offer' | 'rejected';
```

Update `GeneratedCoverLetterEntry`:
```typescript
export interface GeneratedCoverLetterEntry {
  id: number;
  created_at: string;
  company_name: string | null;
  job_description: string;
  extra_context: string | null;
  cover_letter_text: string;
  tone: string;
  job_url: string | null;
  match_score: number | null;
  fit_analysis: FitAnalysisResponse | null;
  application_status: string | null;
  profile_id: number | null;
  profile_label: string | null;
  profile_color: string | null;
  profile_icon: string | null;
}

export interface GeneratedCoverLetterListResponse {
  items: GeneratedCoverLetterEntry[];
  total: number;
}
```

Update `GeneratedCVEntry`:
```typescript
export interface GeneratedCVEntry {
  id: number;
  created_at: string;
  enhanced: boolean;
  profile_snapshot: string;
  application_status: string | null;
  profile_id: number | null;
  profile_label: string | null;
  profile_color: string | null;
  profile_icon: string | null;
}

export interface GeneratedCVListResponse {
  items: GeneratedCVEntry[];
  total: number;
}
```

Update `CoverLetterRequest`:
```typescript
export interface CoverLetterRequest {
  profile_id: number;
  job_description: string;
  company_name?: string | null;
  extra_context?: string;
  tone?: Tone;
  job_url?: string | null;
  fit_context?: string | null;
  match_score?: number | null;       // from fit analysis — persisted to DB
  fit_analysis_json?: string | null; // JSON string of FitAnalysisResponse — persisted to DB
}
```

- [ ] **Step 2: Add new API functions to `api.ts`**

```typescript
// Scrape
export const scrapeJob = (url: string) =>
  request<ScrapeJobResponse>('/scrape/job', { method: 'POST', body: JSON.stringify({ url }) });

// Fit analysis
export const analyzeFit = (profile_id: number, job_description: string) =>
  request<FitAnalysisResponse>('/analyze/fit', {
    method: 'POST',
    body: JSON.stringify({ profile_id, job_description }),
  });

// Cover letter — streaming (returns raw Response for SSE)
export const generateCoverLetterStream = (data: CoverLetterRequest): Promise<Response> =>
  fetch(`${BASE_URL}/generate/cover-letter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

// History — updated signatures
export interface CoverLetterHistoryFilters {
  profile_id?: number;
  search?: string;
  match_min?: number;
  match_max?: number;
  status?: string;
  sort?: 'date_desc' | 'date_asc' | 'match_desc' | 'company_asc';
  limit?: number;
  offset?: number;
}

export const getCoverLetterHistory = (filters: CoverLetterHistoryFilters = {}) => {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null) params.set(k, String(v));
  }
  const qs = params.toString();
  return request<GeneratedCoverLetterListResponse>(`/history/cover-letter${qs ? `?${qs}` : ''}`);
};

export const getCvHistory = (filters: { profile_id?: number; sort?: string; limit?: number; offset?: number } = {}) => {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null) params.set(k, String(v));
  }
  const qs = params.toString();
  return request<GeneratedCVListResponse>(`/history/cv${qs ? `?${qs}` : ''}`);
};

export const updateCoverLetterStatus = (id: number, status: string | null) =>
  request<GeneratedCoverLetterEntry>(`/history/cover-letter/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });

export const updateCvStatus = (id: number, status: string | null) =>
  request<GeneratedCVEntry>(`/history/cv/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });

export const bulkDeleteCoverLetters = (ids: number[]) =>
  request<{ deleted: number }>('/history/cover-letter', {
    method: 'DELETE',
    body: JSON.stringify({ ids }),
  });

export const bulkDeleteCvs = (ids: number[]) =>
  request<{ deleted: number }>('/history/cv', {
    method: 'DELETE',
    body: JSON.stringify({ ids }),
  });
```

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/lib/types.ts frontend/src/lib/api.ts
rtk git commit -m "feat: add Smart URL types and API functions"
```

---

### Task 11: Cover Letter Page Revamp

**Files:**
- Modify: `frontend/src/routes/cover-letter/+page.svelte`

- [ ] **Step 1: Add URL import tab, fit analysis, tone selector, streaming**

Replace the entire file content. Key changes from the original:
- Tab switcher: "Paste Text" (default) | "Import from URL"
- URL import: input + Import button → calls `scrapeJob`, fills textarea + company name
- Analyze Fit button (shown when `jobDescription.length > 0`) → calls `analyzeFit`, shows analysis card
- Analysis card: match score bar, pros/cons, missing keywords, red flags, suggested emphasis (Accept button), interview prep (collapsed)
- Tone selector: 4 buttons (Professional / Enthusiastic / Concise / Creative)
- Generate → uses `generateCoverLetterStream`, reads SSE with fetch + ReadableStream

```svelte
<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import {
    analyzeFit,
    generateCoverLetterPdf,
    generateCoverLetterStream,
    getProfile,
    scrapeJob,
  } from '$lib/api';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Textarea } from '$lib/components/ui/textarea';
  import { toastState } from '$lib/toast.svelte';
  import type { FitAnalysisResponse, ProfileData, Tone } from '$lib/types';
  import { Check, Copy, Download, Link, Lock, Mail, Printer, Sparkles, UserRoundPen } from '@lucide/svelte';

  let { data } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  // --- Form state ---
  let inputTab = $state<'paste' | 'url'>('paste');
  let jobUrl = $state('');
  let scraping = $state(false);
  let companyName = $state('');
  let jobDescription = $state('');
  let extraContext = $state('');
  let tone = $state<Tone>('professional');

  // --- Fit analysis state ---
  let analyzing = $state(false);
  let fitResult = $state<FitAnalysisResponse | null>(null);
  let showInterviewPrep = $state(false);
  let fitCollapsed = $state(false);

  // --- Generate state ---
  let coverLetterText = $state('');
  let loading = $state(false);
  let downloading = $state(false);
  let copied = $state(false);

  let activeProfileData: ProfileData | null = $state(null);
  let profileLoading = $state(true);

  const TONES: { value: Tone; label: string }[] = [
    { value: 'professional', label: 'Professional' },
    { value: 'enthusiastic', label: 'Enthusiastic' },
    { value: 'concise', label: 'Concise' },
    { value: 'creative', label: 'Creative' },
  ];

  const matchColor = $derived(
    fitResult === null
      ? ''
      : fitResult.match_score >= 70
        ? 'text-green-600 bg-green-500'
        : fitResult.match_score >= 40
          ? 'text-yellow-600 bg-yellow-500'
          : 'text-red-600 bg-red-500'
  );

  const isProfileEmpty = $derived(
    !profileLoading &&
    (!activeProfileData ||
      (activeProfileData.work_experience.length === 0 &&
        activeProfileData.skills.length === 0 &&
        activeProfileData.education.length === 0))
  );

  $effect(() => {
    const ap = activeProfile.current;
    activeProfileData = null;
    coverLetterText = '';
    profileLoading = true;
    if (!ap) { profileLoading = false; return; }
    getProfile(ap.id)
      .then((p) => { activeProfileData = p; })
      .catch(() => {})
      .finally(() => { profileLoading = false; });
  });

  // --- URL import ---
  async function handleImport() {
    if (!jobUrl.trim()) return;
    scraping = true;
    try {
      const res = await scrapeJob(jobUrl.trim());
      jobDescription = res.job_description;
      if (res.company_name) companyName = res.company_name;
      inputTab = 'paste';
      toastState.success('Job posting imported!');
    } catch (e: any) {
      toastState.error(e.message);
    } finally {
      scraping = false;
    }
  }

  // --- Fit analysis ---
  async function handleAnalyzeFit() {
    const ap = activeProfile.current;
    if (!ap || !jobDescription.trim()) return;
    analyzing = true;
    fitResult = null;
    try {
      fitResult = await analyzeFit(ap.id, jobDescription);
      fitCollapsed = false;
    } catch (e: any) {
      toastState.error(e.message);
    } finally {
      analyzing = false;
    }
  }

  function acceptSuggestedEmphasis() {
    if (fitResult) extraContext = fitResult.suggested_emphasis;
  }

  // --- Streaming generation ---
  async function handleGenerate() {
    const ap = activeProfile.current;
    if (!ap || !jobDescription.trim()) return;
    loading = true;
    coverLetterText = '';
    fitCollapsed = true;
    try {
      const resp = await generateCoverLetterStream({
        profile_id: ap.id,
        job_description: jobDescription,
        extra_context: extraContext,
        company_name: companyName.trim() || null,
        tone,
        job_url: jobUrl.trim() || null,
        fit_context: fitResult?.suggested_emphasis || null,
        match_score: fitResult?.match_score ?? null,
        fit_analysis_json: fitResult ? JSON.stringify(fitResult) : null,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Generation failed' }));
        throw new Error(err.detail ?? 'Generation failed');
      }
      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6);
          if (payload === '[DONE]') { loading = false; break; }
          if (payload.startsWith('[ERROR]')) {
            toastState.error(payload.slice(8));
            loading = false;
            return;
          }
          coverLetterText += payload;
        }
      }
      toastState.success('Cover Letter Generated!');
    } catch (e: any) {
      toastState.error(`Generation failed: ${e.message}`);
    } finally {
      loading = false;
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(coverLetterText);
    copied = true;
    toastState.info('Copied to clipboard');
    setTimeout(() => (copied = false), 2000);
  }

  async function handleDownloadPdf() {
    if (!coverLetterText) return;
    downloading = true;
    try {
      const escaped = coverLetterText
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const html = `<div style="font-family:sans-serif;font-size:13px;line-height:1.6;padding:40px;white-space:pre-wrap">${escaped}</div>`;
      const blob = await generateCoverLetterPdf({ html });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'cover-letter.pdf'; a.click();
      URL.revokeObjectURL(url);
      toastState.success('PDF Downloaded!');
    } catch (e: any) {
      toastState.error(`Download failed: ${e.message}`);
    } finally {
      downloading = false;
    }
  }
</script>

<div class="space-y-8 max-w-4xl pb-10 relative">
  <!-- Sticky Header -->
  <div class="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border -mx-4 px-4 py-4 mb-8">
    <div class="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-4 max-w-4xl mx-auto">
      <div>
        <h1 class="text-2xl font-bold flex items-center gap-2">
          <Mail class="w-6 h-6 text-primary" />
          Cover Letter Generator
        </h1>
        <p class="text-xs text-muted-foreground mt-0.5">Import a job URL or paste the description, analyze your fit, and generate a tailored letter.</p>
      </div>
    </div>
  </div>

  <div class="grid lg:grid-cols-[1fr_1.5fr] gap-8 items-start">
    <div class="sticky top-6 z-10 pt-2 pb-6 max-h-[calc(100vh-3rem)] overflow-y-auto">
      <Card class="shadow-sm">
        <CardContent class="p-6 space-y-5">

          <!-- Company name -->
          <div class="space-y-2">
            <Label for="company">Company Name <span class="text-muted-foreground text-xs">(optional)</span></Label>
            <Input id="company" bind:value={companyName} placeholder="e.g. Acme Corp" />
          </div>

          <!-- Job description tab switcher -->
          <div class="space-y-2">
            <Label class="font-semibold text-base">Job Description *</Label>
            <div class="flex gap-1 border-b border-border mb-2">
              <button
                class="px-3 py-1.5 text-sm font-medium transition-colors {inputTab === 'paste' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
                onclick={() => (inputTab = 'paste')}
              >Paste Text</button>
              <button
                class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors {inputTab === 'url' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
                onclick={() => (inputTab = 'url')}
              ><Link class="w-3.5 h-3.5" /> Import URL</button>
            </div>

            {#if inputTab === 'url'}
              <div class="flex gap-2">
                <Input bind:value={jobUrl} placeholder="https://boards.greenhouse.io/..." class="flex-1" />
                <Button onclick={handleImport} disabled={scraping || !jobUrl.trim()} size="sm">
                  {scraping ? 'Fetching…' : 'Import'}
                </Button>
              </div>
              <p class="text-xs text-muted-foreground">Supports Greenhouse, Lever, and most job boards. LinkedIn URLs may not work.</p>
            {:else}
              <Textarea
                id="jd"
                bind:value={jobDescription}
                placeholder="Paste the full job posting here..."
                rows={10}
                class="bg-background/50 resize-y max-h-[40vh]"
              />
            {/if}
          </div>

          <!-- Analyze Fit button -->
          {#if jobDescription.length > 0}
            <Button
              variant="outline"
              size="sm"
              class="w-full"
              onclick={handleAnalyzeFit}
              disabled={analyzing}
            >
              {#if analyzing}
                <Sparkles class="w-4 h-4 mr-2 animate-pulse" /> Analyzing…
              {:else}
                <Sparkles class="w-4 h-4 mr-2" /> Analyze Fit
              {/if}
            </Button>
          {/if}

          <!-- Fit analysis card -->
          {#if fitResult && !fitCollapsed}
            <div class="border border-border rounded-lg p-4 space-y-3 bg-muted/30 animate-in fade-in duration-300">
              <!-- Match score -->
              <div class="flex items-center gap-3">
                <span class="text-sm font-semibold">Match Score:</span>
                <div class="flex-1 bg-muted rounded-full h-2">
                  <div
                    class="h-2 rounded-full {matchColor.split(' ')[1]}"
                    style="width: {fitResult.match_score}%"
                  ></div>
                </div>
                <span class="text-sm font-bold {matchColor.split(' ')[0]}">{fitResult.match_score}%</span>
              </div>

              <!-- Pros / Cons -->
              <div class="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p class="font-medium text-green-600 mb-1">✅ Strengths</p>
                  <ul class="space-y-0.5 text-muted-foreground">
                    {#each fitResult.pros as pro}<li>• {pro}</li>{/each}
                  </ul>
                </div>
                <div>
                  <p class="font-medium text-yellow-600 mb-1">⚠️ Gaps</p>
                  <ul class="space-y-0.5 text-muted-foreground">
                    {#each fitResult.cons as con}<li>• {con}</li>{/each}
                  </ul>
                </div>
              </div>

              <!-- Missing keywords -->
              {#if fitResult.missing_keywords.length > 0}
                <div class="text-xs">
                  <span class="font-medium text-muted-foreground">Missing keywords: </span>
                  {#each fitResult.missing_keywords as kw}
                    <span class="inline-block bg-muted border border-border rounded px-1.5 py-0.5 mr-1 mb-1">{kw}</span>
                  {/each}
                </div>
              {/if}

              <!-- Red flags -->
              {#each fitResult.red_flags as flag}
                <p class="text-xs text-red-600">🚨 {flag}</p>
              {/each}

              <!-- Suggested emphasis -->
              <div class="text-xs border-t border-border pt-3">
                <p class="font-medium mb-1">💡 Suggested emphasis:</p>
                <p class="text-muted-foreground italic">{fitResult.suggested_emphasis}</p>
                <button
                  onclick={acceptSuggestedEmphasis}
                  class="mt-2 text-primary underline text-xs hover:no-underline"
                >Accept suggestion →</button>
              </div>

              <!-- Interview prep (collapsible) -->
              <div class="border-t border-border pt-2">
                <button
                  class="flex items-center gap-2 text-xs font-medium w-full"
                  onclick={() => (showInterviewPrep = !showInterviewPrep)}
                >
                  🎤 Interview prep questions {showInterviewPrep ? '▲' : '▼'}
                </button>
                {#if showInterviewPrep}
                  <ul class="mt-2 space-y-1 text-xs text-muted-foreground">
                    {#each fitResult.interview_questions as q}<li>• {q}</li>{/each}
                  </ul>
                {/if}
              </div>

              <!-- Re-analyze -->
              <button
                onclick={handleAnalyzeFit}
                disabled={analyzing}
                class="text-xs text-muted-foreground underline hover:no-underline"
              >Re-analyze</button>
            </div>
          {/if}

          <!-- Extra context / emphasis -->
          <div class="space-y-2">
            <Label for="extra" class="font-semibold text-base">
              What to emphasize <span class="text-muted-foreground text-xs font-normal">(optional)</span>
            </Label>
            <Textarea
              id="extra"
              bind:value={extraContext}
              placeholder="Focus on my open source contributions..."
              rows={3}
              class="bg-background/50 resize-y max-h-[20vh]"
            />
          </div>

          <!-- Tone selector -->
          <div class="space-y-2">
            <Label class="font-semibold text-sm">Tone</Label>
            <div class="flex gap-1 flex-wrap">
              {#each TONES as t}
                <button
                  onclick={() => (tone = t.value)}
                  class="px-3 py-1.5 text-xs rounded-md border transition-colors
                    {tone === t.value
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border text-muted-foreground hover:text-foreground hover:bg-accent'}"
                >{t.label}</button>
              {/each}
            </div>
          </div>

          {#if activeProfile.current}
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 border text-sm">
              <span class="text-base leading-none">{activeProfile.current.icon}</span>
              <span class="font-medium">{activeProfile.current.label}</span>
              <span class="text-muted-foreground text-xs">— writing as this profile</span>
            </div>
          {/if}

          <Button
            onclick={handleGenerate}
            disabled={loading || !jobDescription.trim() || !isOnboarded || isProfileEmpty || profileLoading}
            class="w-full shadow-md"
            size="lg"
          >
            {#if !isOnboarded}
              <Lock class="w-4 h-4 mr-2" /> Locked
            {:else if loading}
              <Sparkles class="w-4 h-4 mr-2 animate-pulse" /> Generating Letter…
            {:else}
              <Sparkles class="w-4 h-4 mr-2" /> Write Cover Letter
            {/if}
          </Button>
        </CardContent>
      </Card>
    </div>

    <!-- Right panel: preview -->
    <div class="space-y-4">
      {#if !coverLetterText && !loading}
        {#if isProfileEmpty}
          <Card class="border-dashed border-2 border-yellow-400/60 bg-yellow-50/30 dark:bg-yellow-900/10 h-full min-h-125 flex items-center justify-center">
            <CardContent class="flex flex-col items-center justify-center p-8 text-center">
              <div class="w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 rounded-full flex items-center justify-center mb-4">
                <UserRoundPen class="w-8 h-8" />
              </div>
              <h3 class="text-lg font-bold mb-2">Profile is empty</h3>
              <p class="text-muted-foreground text-sm max-w-65 mb-5">
                Add your work experience, education, or skills to <strong>{activeProfile.current?.label ?? 'this profile'}</strong> before writing a cover letter.
              </p>
              <Button href="/profile" variant="default" size="sm">Fill in my profile</Button>
            </CardContent>
          </Card>
        {:else}
          <Card class="border-dashed border-2 bg-muted/30 h-full min-h-125 flex items-center justify-center">
            <CardContent class="flex flex-col items-center justify-center p-8 text-center">
              <div class="w-16 h-16 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
                <Mail class="w-8 h-8 opacity-50" />
              </div>
              <h3 class="text-lg font-bold mb-2">No letter generated yet</h3>
              <p class="text-muted-foreground text-sm max-w-62.5">
                Fill out the job description and click generate.
              </p>
            </CardContent>
          </Card>
        {/if}
      {/if}

      {#if loading}
        <div class="space-y-4">
          <div class="flex items-center gap-2 text-sm bg-primary/5 p-3 rounded-lg border border-primary/20 animate-pulse">
            <Sparkles class="w-4 h-4 text-primary" />
            <span class="text-primary font-medium">AI is crafting your letter...</span>
          </div>
          {#if coverLetterText}
            <Card class="shadow-lg border-primary/10">
              <CardContent class="p-0">
                <div class="overflow-hidden bg-white dark:bg-zinc-950/40 rounded-xl transition-colors">
                  <CoverLetterPreview text={coverLetterText} />
                </div>
              </CardContent>
            </Card>
          {:else}
            <Card class="shadow-lg border-primary/10 overflow-hidden">
              <CardContent class="p-8 space-y-6 bg-white dark:bg-zinc-950/40 min-h-125">
                {#each Array(4) as _}
                  <div class="space-y-2">
                    <Skeleton class="h-4 w-full" />
                    <Skeleton class="h-4 w-5/6" />
                  </div>
                {/each}
              </CardContent>
            </Card>
          {/if}
        </div>
      {/if}

      {#if coverLetterText && !loading}
        <div class="animate-in fade-in slide-in-from-right-4 duration-500 space-y-3">
          <div class="flex items-center justify-between px-1">
            <h2 class="font-semibold text-lg flex items-center gap-2">
              <Sparkles class="w-5 h-5 text-amber-500" />
              Generated Letter
            </h2>
            <div class="flex gap-2">
              <Button variant="outline" size="sm" onclick={handleCopy} class="shadow-sm">
                {#if copied}<Check class="w-4 h-4 mr-1 text-green-500" /> Copied
                {:else}<Copy class="w-4 h-4 mr-1" /> Copy{/if}
              </Button>
              <Button variant="outline" size="sm" onclick={handleDownloadPdf} disabled={downloading} class="shadow-sm">
                <Download class="w-4 h-4 mr-1" /> PDF
              </Button>
              <Button variant="outline" size="sm" onclick={() => window.print()} class="shadow-sm hidden xl:flex">
                <Printer class="w-4 h-4 mr-1" /> Print
              </Button>
            </div>
          </div>
          <Card class="shadow-lg border-primary/10">
            <CardContent class="p-0">
              <div class="overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white rounded-xl print:border-0 transition-colors">
                <CoverLetterPreview text={coverLetterText} />
              </div>
            </CardContent>
          </Card>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  @media print {
    :global(header), :global(nav) { display: none !important; }
  }
</style>
```

- [ ] **Step 2: Verify the page loads and URL import works**

Start both servers and test:
```bash
# Terminal 1
cd backend && uv run uvicorn main:app --reload
# Terminal 2
cd frontend && bun dev
```

Navigate to `http://localhost:5173/cover-letter`. Test:
- Tab switch between Paste / Import URL
- Import a Greenhouse URL (e.g. `https://boards.greenhouse.io/figma/jobs/5313748004`)
- Verify company name + job description auto-fill

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/routes/cover-letter/+page.svelte
rtk git commit -m "feat: cover letter page — URL import, fit analysis, tone, streaming"
```

---

### Task 12: History Page Overhaul

**Files:**
- Modify: `frontend/src/routes/history/+page.svelte`

- [ ] **Step 1: Update history page with search, match filter, status tags, bulk delete**

The history page needs these additions to the cover letter tab:
- Search input (debounced 300ms)
- Match score filter dropdown
- Sort dropdown
- Application status dropdown on each card
- Bulk delete checkboxes + "Delete selected (N)" button
- Match score badge on cover letter cards

Add to the script section (cover letter tab only — CV tab minimal changes):

```svelte
<script lang="ts">
  // Replace existing imports and add:
  import {
    bulkDeleteCoverLetters,
    bulkDeleteCvs,
    deleteCoverLetterHistoryEntry,
    deleteCvHistoryEntry,
    getCoverLetterHistory,
    getCvHistory,
    updateCoverLetterStatus,
    updateCvStatus,
  } from '$lib/api';
  import { toastState } from '$lib/toast.svelte';
  // ... rest of existing imports

  // Cover letter filters
  let clSearch = $state('');
  let clMatchFilter = $state<'all' | 'high' | 'medium' | 'low'>('all');
  let clSort = $state<'date_desc' | 'date_asc' | 'match_desc' | 'company_asc'>('date_desc');
  let clTotal = $state(0);
  let clSearchTimer: ReturnType<typeof setTimeout>;

  // Bulk delete
  let selectedClIds = $state<Set<number>>(new Set());
  let selectedCvIds = $state<Set<number>>(new Set());
  let confirmBulkDelete = $state(false);

  // Status options
  const STATUS_OPTIONS = [
    { value: null, label: '—' },
    { value: 'applied', label: 'Applied' },
    { value: 'interviewing', label: 'Interviewing' },
    { value: 'offer', label: 'Offer' },
    { value: 'rejected', label: 'Rejected' },
  ];

  async function loadCoverLetters() {
    const filters: any = { sort: clSort };
    if (filterProfileId != null) filters.profile_id = filterProfileId;
    if (clSearch) filters.search = clSearch;
    if (clMatchFilter === 'high') filters.match_min = 70;
    else if (clMatchFilter === 'medium') { filters.match_min = 40; filters.match_max = 69; }
    else if (clMatchFilter === 'low') filters.match_max = 39;
    const res = await getCoverLetterHistory(filters);
    clItems = res.items;
    clTotal = res.total;
  }

  async function handleClStatusChange(id: number, status: string | null) {
    try {
      const updated = await updateCoverLetterStatus(id, status);
      clItems = clItems.map((e) => (e.id === id ? updated : e));
    } catch (e: any) {
      toastState.error(e.message);
    }
  }

  async function handleBulkDeleteCl() {
    try {
      await bulkDeleteCoverLetters([...selectedClIds]);
      clItems = clItems.filter((e) => !selectedClIds.has(e.id));
      selectedClIds = new Set();
      confirmBulkDelete = false;
    } catch (e: any) {
      toastState.error(e.message);
    }
  }
</script>
```

For the cover letter list UI, add match score badge, status dropdown, and checkboxes to each card. Replace the cover-letter list section:

```svelte
<!-- In the cover-letter tab, replace the list section with: -->
<!-- Filter bar -->
<div class="flex items-center gap-2 flex-wrap mb-4">
  <input
    class="flex-1 min-w-[160px] bg-card border border-border rounded-md px-3 py-1.5 text-sm"
    placeholder="🔍 Search company or role..."
    bind:value={clSearch}
    oninput={() => { clearTimeout(clSearchTimer); clSearchTimer = setTimeout(loadCoverLetters, 300); }}
  />
  <select
    class="bg-card border border-border rounded-md px-2 py-1.5 text-sm"
    bind:value={clMatchFilter}
    onchange={loadCoverLetters}
  >
    <option value="all">All matches</option>
    <option value="high">High (≥70%)</option>
    <option value="medium">Medium (40–69%)</option>
    <option value="low">Low (&lt;40%)</option>
  </select>
  <select
    class="bg-card border border-border rounded-md px-2 py-1.5 text-sm"
    bind:value={clSort}
    onchange={loadCoverLetters}
  >
    <option value="date_desc">Newest first</option>
    <option value="date_asc">Oldest first</option>
    <option value="match_desc">Best match</option>
    <option value="company_asc">Company A–Z</option>
  </select>
  {#if selectedClIds.size > 0}
    <button
      onclick={() => (confirmBulkDelete = true)}
      class="px-3 py-1.5 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90"
    >Delete selected ({selectedClIds.size})</button>
  {/if}
</div>

{#if confirmBulkDelete}
  <div class="border border-destructive/30 rounded-lg p-3 bg-destructive/5 flex items-center gap-3 mb-3">
    <p class="text-sm flex-1">Delete {selectedClIds.size} cover letter(s)?</p>
    <button onclick={handleBulkDeleteCl} class="text-sm text-destructive underline">Confirm</button>
    <button onclick={() => (confirmBulkDelete = false)} class="text-sm text-muted-foreground underline">Cancel</button>
  </div>
{/if}
```

For each cover letter card, add match score badge + status dropdown + checkbox:

```svelte
{#each clItems as entry}
  <div class="flex items-start gap-2">
    <input
      type="checkbox"
      class="mt-3 rounded"
      checked={selectedClIds.has(entry.id)}
      onchange={() => {
        const s = new Set(selectedClIds);
        if (s.has(entry.id)) s.delete(entry.id); else s.add(entry.id);
        selectedClIds = s;
      }}
    />
    <button
      onclick={() => selectedCl = entry}
      class="flex-1 text-left border rounded-lg p-3 transition-colors hover:bg-accent
        {selectedCl?.id === entry.id ? 'border-primary bg-accent' : 'bg-card'}"
    >
      <div class="flex items-center justify-between gap-2">
        <span class="text-sm font-medium truncate">{displayCompany(entry)}</span>
        <div class="flex items-center gap-1.5 shrink-0">
          {#if entry.match_score !== null}
            <span class="text-xs px-1.5 py-0.5 rounded font-medium
              {entry.match_score >= 70 ? 'bg-green-500/10 text-green-600'
               : entry.match_score >= 40 ? 'bg-yellow-500/10 text-yellow-600'
               : 'bg-red-500/10 text-red-600'}">{entry.match_score}%</span>
          {/if}
          {#if entry.tone && entry.tone !== 'professional'}
            <span class="text-xs bg-muted border border-border rounded px-1.5 py-0.5 capitalize">{entry.tone}</span>
          {/if}
          {#if entry.profile_color && entry.profile_icon}
            <span class="flex items-center gap-1 text-xs text-muted-foreground">
              <span class="w-2 h-2 rounded-full" style="background:{entry.profile_color}"></span>
              {entry.profile_icon}
            </span>
          {/if}
        </div>
      </div>
      <div class="text-xs text-muted-foreground mt-0.5">{formatDate(entry.created_at)}</div>
      <!-- Status dropdown -->
      <div class="mt-2" onclick={(e) => e.stopPropagation()}>
        <select
          class="text-xs bg-background border border-border rounded px-2 py-1"
          value={entry.application_status ?? ''}
          onchange={(e) => handleClStatusChange(entry.id, (e.target as HTMLSelectElement).value || null)}
        >
          {#each STATUS_OPTIONS as opt}
            <option value={opt.value ?? ''}>{opt.label}</option>
          {/each}
        </select>
      </div>
    </button>
  </div>
{/each}
```

- [ ] **Step 2: Update `$effect` in history page to call `loadCoverLetters` instead of `getCoverLetterHistory` directly**

Find the existing `$effect` (lines ~33–51) and replace it with this version that preserves loading state, error handling, selected-item reset, and the stale-response sequence guard:

```svelte
$effect(() => {
  const pid = filterProfileId;
  const seq = ++loadSeq;
  loading = true;
  errorMsg = '';
  selectedCv = null;
  selectedCl = null;
  // CV tab — simple call unchanged
  getCvHistory(pid !== undefined ? { profile_id: pid } : {})
    .then((r) => {
      if (seq !== loadSeq) return;
      cvItems = r.items;
    })
    .catch((e: any) => {
      if (seq !== loadSeq) return;
      errorMsg = e.message;
    })
    .finally(() => {
      if (seq !== loadSeq) return;
      loading = false;
    });
  // Cover letter tab — use filter-aware loader (manages clItems/clTotal)
  loadCoverLetters();
});
```

- [ ] **Step 3: Verify history filters work end to end**

Navigate to `http://localhost:5173/history`, switch to Cover Letters tab. Test:
- Search by company name
- Filter by match score (generate a cover letter with fit analysis first)
- Change application status on a card
- Select multiple and bulk delete

- [ ] **Step 4: Commit**

```bash
rtk git add frontend/src/routes/history/+page.svelte
rtk git commit -m "feat: history page — search, match filter, status tags, bulk delete"
```

---

### Task 13: Push

- [ ] **Step 1: Push all commits**

```bash
rtk git push
```
