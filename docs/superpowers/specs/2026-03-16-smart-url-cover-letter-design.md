# Smart URL Cover Letter Generator — Design Spec

**Date:** 2026-03-16
**Status:** Approved for implementation

## Overview

Extend the cover letter generation flow with:
1. **URL import** — paste a job posting URL, extract job description automatically
2. **Job fit analysis** — AI-powered match score, pros/cons, missing keywords, red flags, interview prep, and auto-suggested emphasis
3. **Cover letter generation revamp** — streaming output, tone selector, fit context injection
4. **History UX overhaul** — server-side search/filter, match score display, status tags, bulk delete, regenerate

---

## Architecture

### New Backend Endpoints

```
POST /api/scrape/job
POST /api/analyze/fit
```

### Modified Endpoints

```
POST /api/generate/cover-letter   ← add tone, job_url, fit_context, streaming
GET  /api/history/cover-letter    ← add server-side search/filter params
GET  /api/history/cv              ← add server-side search/filter params
```

### New DB Columns (generated_cover_letter table)

```
job_url            TEXT NULL
match_score        INTEGER NULL      -- NULL if Analyze Fit was skipped
fit_analysis       TEXT NULL         -- full FitAnalysisResponse as JSON string, NULL if skipped
tone               TEXT NOT NULL DEFAULT 'professional'
application_status TEXT NULL DEFAULT NULL  -- see ApplicationStatus enum
```

`fit_analysis` stores the complete serialized `FitAnalysisResponse` JSON (all 7 fields). On retrieval, the history detail view deserializes it to reconstruct the analysis card.

### New DB Columns (generated_cv table)

```
application_status TEXT NULL DEFAULT NULL  -- see ApplicationStatus enum
```

### ApplicationStatus Enum

Valid values (enforced in Pydantic schema, stored as TEXT in DB):
```python
class ApplicationStatus(str, Enum):
    applied      = "applied"
    interviewing = "interviewing"
    offer        = "offer"
    rejected     = "rejected"
```
`NULL` means no status set (displayed as `—` in UI).

---

## Section 1: Cover Letter Page UI

### Dual-Mode Job Description Input

Tab switcher above the job description field:

**Tab A — Paste Text** (default, existing behavior)
- Textarea for pasting job description directly — no changes to existing behavior

**Tab B — Import from URL**
- Text input for job posting URL
- "Import" button → calls `POST /api/scrape/job`
- Loading state: spinner + "Fetching job posting…"
- On success: switches to Paste Text tab with textarea pre-filled, company name auto-filled if extracted
- On failure: inline error with message from backend (e.g. "Could not extract — please paste the text manually")

### Analyze Fit Button

Appears below the job description field once `job_description.length > 0`.
- Label: "Analyze Fit"
- Triggers `POST /api/analyze/fit` with `{ profile_id, job_description }`
- Loading state: spinner + "Analyzing…"
- On success: analysis card appears below the button

### Analysis Card

Shown after clicking Analyze Fit. Collapses automatically after the cover letter is generated.

**Layout:**
```
┌──────────────────────────────────────────────────┐
│  Match Score: 78%  ████████░░  [green/yellow/red] │
├──────────────────────────────────────────────────┤
│  ✅ Strengths          │  ⚠️ Gaps                 │
│  • 5+ yrs Python       │  • No AWS experience     │
│  • Open source work    │  • Missing Kubernetes    │
├──────────────────────────────────────────────────┤
│  Missing keywords: [React] [AWS] [K8s]           │
│  🚨 Red flag: "Requires 10+ years experience"    │
├──────────────────────────────────────────────────┤
│  💡 Suggested emphasis:                          │
│  "Highlight your OSS contributions and Python    │
│   depth — the role heavily weights these"        │
│  [Accept suggestion]                             │
├──────────────────────────────────────────────────┤
│  🎤 Interview prep questions  ▼ (collapsed)      │
│    • "Why are you transitioning from X to Y?"    │
│    • "Describe your experience with distributed  │
│       systems."                                  │
│    • "How do you approach cloud migrations?"     │
└──────────────────────────────────────────────────┘
```

Match score color:
- ≥70% → green
- 40–69% → yellow
- <40% → red

"Accept suggestion" → copies suggested_emphasis into the "What to emphasize" textarea.

Re-analyze button appears at the bottom of the card after the user edits "What to emphasize". It re-runs `POST /api/analyze/fit` with the same `job_description` — the updated "What to emphasize" text is not sent (it's a user note, not a factor in analysis). The score and card refresh in place.

### Tone Selector

Single-select row between the "What to emphasize" field and the Generate button:

```
Tone:  [Professional]  [Enthusiastic]  [Concise]  [Creative]
```

Defaults to Professional. Selected tone is passed in the generate request.

---

## Section 2: Backend — Scraping

### `POST /api/scrape/job`

**Request:**
```python
class ScrapeJobRequest(BaseModel):
    url: str
```

**Response:**
```python
class ScrapeJobResponse(BaseModel):
    job_description: str
    company_name: str | None
    source: Literal["greenhouse_api", "lever_api", "jina", "crawl4ai"]
```

**Tiered scraping logic:**

```
1. Detect Greenhouse URL (boards.greenhouse.io / boards-api.greenhouse.io)
   → Hit public JSON API directly (httpx, no browser)
   → Return structured job description

2. Detect Lever URL (jobs.lever.co)
   → Hit public JSON API directly (httpx, no browser)
   → Return structured job description

3. Any other URL → try Jina Reader
   → GET https://r.jina.ai/{url} with free API key
   → Challenge page detection: response is rejected if:
       • len(text) < 200 characters, OR
       • text contains "Access denied", "Just a moment", "Enable JavaScript",
         "Checking your browser", "cf-browser-verification"
   → If valid → return markdown

4. Jina failed/invalid → try Crawl4AI
   → AsyncWebCrawler with BrowserConfig(enable_stealth=True)
   → CrawlerRunConfig(magic=True)
   → Return result.markdown

5. All failed → raise HTTPException(422,
     detail="Could not extract job posting. Please paste the text manually.")
```

**Note:** The `/api/scrape/job` route handler must be declared `async def` (not `def`) to allow awaiting Crawl4AI's `AsyncWebCrawler` directly without a thread executor.

**Provider extensibility:**
The scraping logic lives in `backend/app/services/scraper.py` as a single async function:
```python
async def scrape_job_url(url: str, provider: str = "auto") -> ScrapedJob
```
Future providers (Firecrawl, etc.) add a new branch — no route changes needed. Provider API keys stored in `app_setting` table (same pattern as LLM key).

**Dependencies to add:**
- `crawl4ai` (with Playwright)
- `httpx` (already present)

---

## Section 3: Backend — Fit Analysis

### `POST /api/analyze/fit`

**Request:**
```python
class FitAnalysisRequest(BaseModel):
    profile_id: int
    job_description: str
```

**Response:**
```python
class FitAnalysisResponse(BaseModel):
    match_score: int                    # 0-100
    pros: list[str]                     # profile strengths matching role
    cons: list[str]                     # gaps
    missing_keywords: list[str]         # keywords in JD not in profile
    red_flags: list[str]                # hard blockers, empty list if none
    suggested_emphasis: str             # pre-fill for "What to emphasize"
    interview_questions: list[str]      # 3 questions based on gaps
```

**Implementation:**
- Fetch profile from DB
- Build a structured JSON prompt: profile summary + job description → ask LLM for all 7 fields in one call
- Parse JSON response into `FitAnalysisResponse`
- Logic lives in `backend/app/services/fit_analysis.py`

**LLM prompt structure:**
```
System: You are a career coach analyzing a candidate's fit for a job.
        Return ONLY valid JSON with keys: match_score, pros, cons,
        missing_keywords, red_flags, suggested_emphasis, interview_questions.

User: Profile: {profile_json}
      Job Description: {job_description}
      Analyze fit and return JSON.
```

---

## Section 4: Cover Letter Generation Revamp

### Updated Request Schema

```python
class CoverLetterRequest(BaseModel):
    profile_id: int
    job_description: str
    company_name: str | None = None
    extra_context: str = ""
    tone: Literal["professional", "enthusiastic", "concise", "creative"] = "professional"
    job_url: str | None = None
    fit_context: str | None = None  # free-text note injected into prompt (e.g. suggested_emphasis from fit analysis)
```

### Streaming Response

`POST /api/generate/cover-letter` returns `StreamingResponse` with `media_type="text/event-stream"`.

**SSE format — each chunk:**
```
data: <text chunk>\n\n
```
Chunks are arbitrary strings (whatever litellm yields per token). The stream ends with a sentinel:
```
data: [DONE]\n\n
```

**Error handling mid-stream:** If the LLM raises after streaming has started, send:
```
data: [ERROR] <message>\n\n
```
then close the stream. Frontend detects `[ERROR]` prefix and shows a toast.

**Backend implementation:** Add `stream_llm(provider, api_key, messages)` to `services/llm.py` as an `async generator` using `litellm.acompletion(..., stream=True)`. The existing `call_llm` remains unchanged for non-streaming callers.

**DB write:** Accumulate all chunks server-side inside the generator function. The write happens at the end of the generator itself — after yielding `data: [DONE]\n\n` — before the generator returns. This is the only correct location; writing after `StreamingResponse()` is constructed is not possible. If the stream errors, nothing is saved.

**Frontend parsing — exact algorithm:**
```
for each line in the stream:
  if line starts with "data: ":
    value = line[6:]              // strip "data: " prefix
    if value == "[DONE]":
      stop reading
    elif value starts with "[ERROR]":
      show toast with value[8:]   // strip "[ERROR] " prefix
      stop reading
    else:
      append value to displayed letter
```

### Tone Injection

Each tone maps to a prompt modifier:
```python
TONE_PROMPTS = {
    "professional": "Write in a formal, polished tone.",
    "enthusiastic": "Write in an energetic, passionate tone that conveys genuine excitement.",
    "concise": "Write concisely — aim for under 200 words. No filler.",
    "creative": "Write in a distinctive, memorable style that stands out.",
}
```

### Fit Context Injection

If `fit_context` is provided:
```
Additional context from the candidate: {fit_context}.
Use this to guide emphasis — do not fabricate experience, but frame existing
experience to address these points where honest.
```

---

## Section 5: History UX Overhaul

### Server-Side Filtering

All filtering happens server-side. Frontend sends query params; backend filters and returns paginated results.

**Updated `GET /api/history/cover-letter` params:**
```
profile_id:   int | None
search:       str | None   (searches company_name + job_description)
match_min:    int | None   (minimum match score, 0-100)
match_max:    int | None
status:       str | None   (filter by ApplicationStatus value)
sort:         "date_desc" | "date_asc" | "match_desc" | "company_asc"  default: date_desc
limit:        int = 20
offset:       int = 0
```

**Updated `GET /api/history/cv` params:**
```
profile_id:   int | None
sort:         "date_desc" | "date_asc"  default: date_desc
limit:        int = 20
offset:       int = 0
```

Both return `total: int` alongside `items` for pagination.

### History Page Layout

**Tab structure:** `All` | `Cover Letters` | `CVs`

**Filter/search bar (server-side):**
- Search input (debounced 300ms → triggers new API call)
- Match score filter: All / High (≥70%) / Medium (40–69%) / Low (<40%) — cover letters only
- Sort dropdown
- Profile filter (existing)

**Cover letter history card:**
```
┌─────────────────────────────────────────────────┐
│ 🏢 Acme Corp · Senior Engineer                  │
│ ████████░░  78%  [Professional]  Mar 16, 2026   │
│ 🔵 💼 Default                                   │
│ [Applied ▼]  [View]  [Regenerate]  [Delete]     │
└─────────────────────────────────────────────────┘
```

- Match score bar: green/yellow/red
- Tone badge
- Application status dropdown: `—` / `Applied` / `Interviewing` / `Offer` / `Rejected`
- "View" opens detail panel inline
- "Regenerate" navigates to cover letter page pre-filled with same job description + company

**CV history card:**
```
┌─────────────────────────────────────────────────┐
│ 🔵 💼 Default  [AI Enhanced]  Mar 16, 2026      │
│ [Applied ▼]  [View]  [Print]  [Delete]          │
└─────────────────────────────────────────────────┘
```

**Bulk delete:**
- Checkbox on each card → "Delete selected (N)" button appears in header
- Confirmation dialog before delete

**Empty states:**
- Cover Letters tab empty → "Generate your first cover letter →"
- CVs tab empty → "Generate your first CV →"
- Search returns nothing → "No results for '{query}' — try a different search"

### Application Status

Stored in `application_status` column (nullable TEXT). Updated via:

**`PATCH /api/history/cover-letter/{id}/status`**
**`PATCH /api/history/cv/{id}/status`**

**Request body:**
```python
class UpdateStatusRequest(BaseModel):
    status: ApplicationStatus | None  # None clears status back to —
```

**Response:** `200` with updated entry object (same shape as list entry).

Designed to plug into the full Application Tracker Kanban when built — status values are identical.

### Bulk Delete

**`DELETE /api/history/cover-letter`**
**`DELETE /api/history/cv`**

**Request body:**
```python
class BulkDeleteRequest(BaseModel):
    ids: list[int]
```

**Response:** `200` with `{ "deleted": N }` count. Silently skips IDs that don't exist.

### Updated History Response Schemas

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
    match_score: int | None          # NULL if Analyze Fit was skipped
    fit_analysis: dict | None        # deserialized FitAnalysisResponse, NULL if skipped
    application_status: str | None
    profile_id: int | None
    profile_label: str | None
    profile_color: str | None
    profile_icon: str | None

class GeneratedCoverLetterListResponse(BaseModel):
    items: list[GeneratedCoverLetterEntry]
    total: int                        # total matching records for pagination

class GeneratedCVEntry(BaseModel):
    id: int
    created_at: datetime
    enhanced: bool
    profile_snapshot: str
    application_status: str | None
    profile_id: int | None
    profile_label: str | None
    profile_color: str | None
    profile_icon: str | None

class GeneratedCVListResponse(BaseModel):
    items: list[GeneratedCVEntry]
    total: int
```

---

## Data Flow Summary

```
User pastes URL
  → POST /api/scrape/job
  → job_description + company_name auto-filled

User clicks "Analyze Fit"
  → POST /api/analyze/fit
  → analysis card appears (score, pros, cons, keywords, red flags, questions)
  → user optionally accepts suggested_emphasis

User selects tone, clicks "Generate Cover Letter"
  → POST /api/generate/cover-letter (streaming)
  → letter streams in real time
  → saved to DB with job_url, match_score, fit_analysis, tone
  → analysis card collapses

User views history
  → GET /api/history/cover-letter?search=&match_min=&sort= (server-side)
  → cards show match score, tone, status
  → can regenerate, set status, bulk delete
```

---

## Files to Create / Modify

| File | Action |
|------|--------|
| `backend/app/services/scraper.py` | Create — tiered scraping logic |
| `backend/app/services/fit_analysis.py` | Create — fit analysis LLM logic |
| `backend/app/routes/scrape.py` | Create — POST /api/scrape/job |
| `backend/app/routes/analyze.py` | Create — POST /api/analyze/fit |
| `backend/app/routes/generate.py` | Modify — streaming, tone, fit_context |
| `backend/app/routes/history.py` | Modify — server-side search/filter/pagination, PATCH status, bulk delete |
| `backend/app/schemas.py` | Modify — new request/response schemas |
| `backend/app/models.py` | Modify — new columns on generated_cover_letter + generated_cv |
| `backend/migrations/` | Create — Alembic migration for new columns |
| `backend/main.py` | Modify — register new routers |
| `frontend/src/routes/cover-letter/+page.svelte` | Modify — URL import, analysis card, tone selector, streaming |
| `frontend/src/routes/history/+page.svelte` | Modify — full UX overhaul |
| `frontend/src/lib/api.ts` | Modify — new API functions |
| `frontend/src/lib/types.ts` | Modify — new types |

---

## Out of Scope (Future)

- External scraping provider integrations (Firecrawl etc.) — provider hook is built in, implementation deferred
- Full Application Tracker Kanban — status field is built in, UI deferred
- Pagination UI component — first version loads 20 most recent, load-more button if `total > 20`
