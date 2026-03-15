# ApplyKit — Design Spec
**Date:** 2026-03-14
**Status:** Draft

---

## Overview

ApplyKit is a self-hosted, local-first job application toolkit. Users set up a profile once, then generate ATS-optimized CVs and tailored cover letters powered by an LLM. No login, no cloud dependency — runs entirely on the user's machine.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | SvelteKit + TypeScript + Tailwind CSS + shadcn-svelte |
| Backend | Python + FastAPI |
| LLM | LiteLLM (Gemini default, multi-provider ready) |
| Database | SQLite via SQLAlchemy + Alembic (migrations) |
| CV Import Parsing | pdfplumber (PDF), python-docx (DOCX), plain text |
| PDF Generation | WeasyPrint (server-side, accepts HTML from frontend) + browser print (frontend-only) |
| CV/Letter Rendering | Svelte components (SvelteKit renders HTML preview, no backend templating) |

---

## Architecture

```
SvelteKit (localhost:5173)
        │ HTTP fetch
FastAPI Backend (localhost:8000)
        ├── LiteLLM → Gemini (extensible)
        ├── SQLAlchemy → SQLite @ backend/applykit.db
        ├── pdfplumber / python-docx (CV import)
        └── WeasyPrint (PDF conversion — accepts HTML string from frontend)
```

The API key lives exclusively in `backend/.env` — the frontend never sees it. All LLM calls are proxied through the FastAPI backend.

---

## Project Structure

```
applykit/
├── frontend/                        # SvelteKit app
│   ├── src/
│   │   ├── routes/
│   │   │   ├── /                    # First-run / dashboard
│   │   │   ├── /profile             # Profile setup & edit
│   │   │   ├── /import              # CV import (upload / paste)
│   │   │   ├── /cv                  # CV generate, preview, download
│   │   │   └── /cover-letter        # Cover letter generate, preview
│   │   └── lib/
│   │       └── api.ts               # Typed fetch wrapper for backend
│   ├── tailwind.config.ts
│   └── package.json
│
├── backend/                         # FastAPI app
│   ├── app/
│   │   ├── main.py                  # App entrypoint, runs DB migration on startup
│   │   ├── routes/
│   │   │   ├── profile.py
│   │   │   ├── generate.py
│   │   │   └── import_cv.py
│   │   ├── services/
│   │   │   ├── llm.py               # LiteLLM wrapper + API key check
│   │   │   ├── pdf.py               # WeasyPrint PDF generation
│   │   │   └── parser.py            # pdfplumber + python-docx + text
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   └── database.py              # DB session setup
│   ├── alembic/                     # DB migrations
│   ├── .env                         # LLM_API_KEY, LLM_PROVIDER
│   ├── .env.example                 # Template for users to copy
│   └── requirements.txt
│
└── README.md
```

---

## Database Initialization

On every startup, `main.py` runs `alembic upgrade head` programmatically before accepting requests. This creates `backend/applykit.db` if it does not exist, and applies any pending migrations. Users do not need to run migrations manually.

---

## Data Model

Single `profile` table — always one row (`id = 1`). `POST /api/profile` performs an upsert: inserts if no row exists, updates otherwise.

```
profile
├── id                  INTEGER PRIMARY KEY (always 1)
├── name                TEXT
├── email               TEXT
├── phone               TEXT
├── location            TEXT
├── linkedin            TEXT
├── github              TEXT
├── portfolio           TEXT
├── summary             TEXT
├── work_experience     TEXT (JSON array)
├── education           TEXT (JSON array)
├── skills              TEXT (JSON array of strings)
├── projects            TEXT (JSON array)
├── certifications      TEXT (JSON array)
└── updated_at          DATETIME
```

JSON fields are stored as TEXT in SQLite and serialized/deserialized via Pydantic.

---

## API Endpoints

### Standard Response Shapes

**Error response (all errors):**
```json
{ "detail": "Human-readable message", "code": "MACHINE_READABLE_CODE" }
```

Error codes used in client logic (not just for display):
- `API_KEY_NOT_CONFIGURED`
- `LLM_CALL_FAILED`
- `PDF_RENDER_FAILED`
- `FILE_PARSE_FAILED`
- `FILE_TYPE_UNSUPPORTED`
- `FILE_TOO_LARGE`
- `LLM_OUTPUT_INVALID`
- `PROFILE_NOT_FOUND`

**Success response (non-data endpoints):**
```json
{ "ok": true }
```

---

#### `GET /api/status`

Check whether `LLM_API_KEY` and `LLM_PROVIDER` are present and non-empty in `.env`.

This is an **env-var presence check only** — no live probe to the provider. The field is named `api_key_configured` to reflect this accurately.

Response `200`:
```json
{ "api_key_configured": true, "provider": "gemini/gemini-1.5-flash" }
{ "api_key_configured": false, "provider": null }
```

---

#### `GET /api/profile`

Fetch the saved profile.

- If profile row exists: `200` with full profile JSON.
- If no profile row: `200` with `{ "profile": null }` — **not a 404**. The frontend uses `profile === null` to detect first-run state. A 404 would be ambiguous with routing errors.

---

#### `POST /api/profile`

Create or update profile (upsert to `id = 1`).

Request body: full profile JSON. `name` and `email` are required; all other fields are optional.
Response `200`: Updated profile JSON.

---

#### `POST /api/import/cv`

Parse an uploaded file or plain text and extract profile fields via LLM.

Request: `multipart/form-data` with either:
- `file`: PDF or DOCX (validated by MIME type + extension, max 5MB)
- `text`: plain text string

**If both `file` and `text` are provided:** `file` takes precedence; `text` is ignored.

File validation:
- Accepted MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Accepted extensions: `.pdf`, `.docx`
- Max size: 5MB

Response `200`: Extracted profile JSON (same shape as profile model). **This is a preview — it is NOT saved to the database.** The frontend renders it in the editable profile form for review.

**Import behavior when profile already exists:** The frontend detects this via `GET /api/profile` returning a non-null profile. It shows a confirmation dialog: *"This will replace all current profile fields. Continue?"* (full replace, no field-by-field merge). The user can edit extracted fields freely before clicking Save, which calls `POST /api/profile`.

Errors (all include `code` field):
- `400 API_KEY_NOT_CONFIGURED`: LLM call would fail, surface early
- `422 FILE_TYPE_UNSUPPORTED`: unsupported extension or MIME type
- `413 FILE_TOO_LARGE`: file exceeds 5MB
- `422 FILE_PARSE_FAILED`: valid type but unreadable/corrupt or extracted text < 100 chars
- `422 LLM_OUTPUT_INVALID`: LLM returned output that failed profile schema validation
- `502 LLM_CALL_FAILED`: LLM provider error or timeout

---

#### `POST /api/generate/cv`

Generate ATS-optimized CV data.

Request body: none. Backend reads the saved profile from DB, calls LLM to enhance `summary` and `work_experience` bullets for ATS, and returns the enhanced data as JSON.

The enhanced content is **not persisted** — the user's saved profile is unchanged. The frontend receives the data and renders the CV preview using a Svelte component. If the user wants to keep the ATS-enhanced version, they edit it in `/profile`.

A UI note is shown on the `/cv` page: *"Generate CV uses your saved profile. Make sure your profile is up to date before generating."*

Response `200`:
```json
{
  "enhanced": true,
  "profile": { /* full profile shape, summary + work_experience may be ATS-enhanced */ }
}
```

**`enhanced` field:** `true` if LLM enhancement succeeded, `false` if it failed and the original profile data was used as fallback. The frontend uses this to optionally show a notice: *"ATS enhancement failed — showing original profile data."*

**ATS enhancement fallback:** If the LLM returns invalid output, the backend sets `enhanced: false` and returns the original profile without erroring — the user still gets a valid CV.

Response `400 API_KEY_NOT_CONFIGURED`
Response `404 PROFILE_NOT_FOUND`
Response `502 LLM_CALL_FAILED`

---

#### `POST /api/generate/cv/pdf`

Convert a rendered CV HTML string to a downloadable PDF via WeasyPrint.

Request body: `{ "html": "<full HTML string rendered by the SvelteKit CV component>" }`

The frontend renders the CV Svelte component to an HTML string, then POSTs it here. WeasyPrint converts it to PDF.

**CSS/font requirement:** The HTML must be self-contained. The SvelteKit CV component achieves this by using only Tailwind utility classes (purged at build time to a `<style>` block) and no external CDN font imports. System fonts only (`font-family: serif` or `sans-serif`). This is a known constraint — the PDF and browser preview will use system fonts, not custom web fonts. Documented in README as a known limitation.

Response `200`: PDF binary stream (`Content-Type: application/pdf`, `Content-Disposition: attachment; filename="cv.pdf"`).
Response `502 PDF_RENDER_FAILED`: WeasyPrint conversion error.

**Browser print:** `window.print()` on the CV preview page is a frontend-only action — no backend call needed.

---

#### `POST /api/generate/cover-letter`

Generate a tailored cover letter from a job description.

Request body:
```json
{
  "job_description": "string (required)",
  "extra_context": "string (optional, default empty)"
}
```

The cover letter endpoint is **stateless** — it reads the profile from DB and generates from the request body each time. This is intentional: the JD and context are one-off inputs, not stored. The user always provides them fresh.

**Design note on CV vs cover letter statefulness:** CV generation reads the saved profile (stateful); cover letter regenerates fully from request body (stateless). Both read the profile from DB. The implication: if the user edits the profile form without saving, the generated CV will use the old data. The UI shows a "Save profile" button prominently on `/profile` and reminds users on `/cv`.

Response `200`:
```json
{
  "cover_letter_text": "plain text cover letter"
}
```

The backend returns plain text only. The frontend renders it in a Svelte component for preview. `plain_text` is also used directly for the copy-to-clipboard button — no HTML stripping needed.

Response `400 API_KEY_NOT_CONFIGURED`
Response `404 PROFILE_NOT_FOUND`
Response `502 LLM_CALL_FAILED`

---

#### `POST /api/generate/cover-letter/pdf`

Convert a rendered cover letter HTML string to a downloadable PDF.

Request body: `{ "html": "<full HTML string rendered by the SvelteKit cover letter component>" }`

Same pattern as the CV PDF endpoint — frontend renders to HTML, POSTs here, WeasyPrint converts. Stateless.

Response `200`: PDF binary stream.
Response `502 PDF_RENDER_FAILED`: WeasyPrint conversion error.

---

## LLM Abstraction

`services/llm.py` exposes a single function:

```python
def call_llm(prompt: str, timeout: int = 30) -> str:
    # 1. Check LLM_PROVIDER and LLM_API_KEY in env — raise APIKeyNotConfiguredError if missing
    # 2. Call litellm.completion(model=LLM_PROVIDER, messages=[{"role": "user", "content": prompt}], timeout=timeout)
    # 3. Raise LLMCallError on any provider exception
    # No retries in MVP — failures surface immediately to the user
```

**Timeout:** 30 seconds. If the provider does not respond within 30 seconds, `LLMCallError` is raised and the frontend receives `502`. The UI shows the error and allows the user to retry manually.

**No automatic retries** in MVP — transient failures are surfaced to the user immediately.

---

## LLM Prompts

### 1. CV Import Extraction

```
System: You are a CV parser. Extract all information from the provided CV text and
return it as a JSON object matching the schema below. Return only valid JSON with
no markdown wrapping or explanation.

Schema: { name, email, phone, location, linkedin, github, portfolio, summary,
  work_experience: [{ company, role, start_date, end_date, bullets[] }],
  education: [{ institution, degree, field, start_date, end_date }],
  skills: [string],
  projects: [{ name, description, tech_stack[], link }],
  certifications: [{ name, issuer, date }]
}

User: <raw CV text>
```

Output validated via Pydantic. On validation failure: `422 LLM_OUTPUT_INVALID`.

### 2. CV ATS Enhancement

```
System: You are an expert CV writer specializing in ATS optimization. Given this
candidate's profile, rewrite the work_experience bullet points and summary to be
action-oriented, metric-driven, and ATS-friendly. Return only valid JSON with two
keys: "summary" (string) and "work_experience" (array, same schema as input).

User: <profile JSON>
```

Output used only for HTML/PDF rendering. Not persisted.

### 3. Cover Letter Generation

```
System: You are an expert career coach. Write a professional, tailored cover letter
based on the candidate's profile and the provided job description. Be specific to
the role and company. Tone: confident, direct. Return plain text only — no subject
line, no date, no header.

User:
Candidate profile: <profile JSON>
Job description: <job_description>
Additional context: <extra_context or "None">
```

Output: plain text cover letter. The frontend renders this in a Svelte component for preview.

---

## First-Run Experience (`/` route)

On app load, the frontend calls `GET /api/status` and `GET /api/profile` in parallel.

| State | UI shown |
|---|---|
| `profile: null` + `api_key_configured: false` | Welcome banner: "Step 1: configure your API key (see README). Step 2: set up your profile." + button to `/profile` |
| `profile: null` + `api_key_configured: true` | Banner: "Profile not set up yet." + button to `/profile` |
| `profile: exists` + `api_key_configured: false` | Warning banner: "API key not configured — generation is disabled." (🔴 in nav). Dashboard quick actions visible but disabled. |
| `profile: exists` + `api_key_configured: true` | Full dashboard. Quick actions: Generate CV, Generate Cover Letter. (🟢 provider name in nav) |

---

## API Key Setup (User Onboarding)

Configuration is manual — no UI endpoint for setting the key (keeps it off all HTTP surfaces):

1. Copy `backend/.env.example` → `backend/.env`
2. Set `LLM_PROVIDER=gemini/gemini-1.5-flash` and `LLM_API_KEY=your-key`
3. Restart the backend

The README explains where to get a free Gemini API key (Google AI Studio link). The nav status indicator updates on every page load via `GET /api/status`.

---

## Error Handling Summary

| Scenario | HTTP | `code` |
|---|---|---|
| API key not set | 400 | `API_KEY_NOT_CONFIGURED` |
| LLM provider error / timeout | 502 | `LLM_CALL_FAILED` |
| File parse failure | 422 | `FILE_PARSE_FAILED` |
| Unsupported file type | 422 | `FILE_TYPE_UNSUPPORTED` |
| File too large (>5MB) | 413 | `FILE_TOO_LARGE` |
| LLM output fails schema validation | 422 | `LLM_OUTPUT_INVALID` |
| Profile not found | 404 | `PROFILE_NOT_FOUND` |
| WeasyPrint PDF conversion error | 502 | `PDF_RENDER_FAILED` |

---

## Out of Scope (MVP)

- User authentication / multi-user
- Job description URL crawling (planned future feature)
- Multiple CV templates (one clean ATS template for MVP)
- CV version history
- Job application tracker
- UI for setting API key (manual `.env` edit only)
- LLM retry logic
- Live API key validation (presence check only)
