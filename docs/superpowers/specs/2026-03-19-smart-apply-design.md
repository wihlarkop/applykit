# Smart Apply — Design Spec

**Date:** 2026-03-19
**Status:** Approved (revised after spec review)

## Overview

Smart Apply is a guided workflow that chains all of ApplyKit's existing features — job scraping, fit analysis, CV generation, and cover letter generation — into a single page. The user pastes a job URL, reviews the fit analysis, configures what to generate, and hits one button. The result is automatically added to the Application Tracker.

## Goals

- Remove friction from the most common workflow: find a job → tailor documents → track application
- Minimal backend changes — chains existing APIs; only adds `application_id` as an optional param to two existing generation endpoints
- Always creates an Application record (Smart Apply implies intent to track)
- User controls what gets generated and how

## User Flow

```
1. Paste job URL (or paste raw text)
       ↓
2. Auto-run: scrape job + fit analysis (parallel where possible)
       ↓
3. Review fit results (score, pros, cons, missing keywords)
       ↓
4. Confirm/edit company name + role title (editable fields)
       ↓
5. Choose what to generate + configure inline
       ↓
6. "Generate & Track" button
       ↓
7. Create Application record FIRST → get application_id
       ↓
8. Generate CV with application_id (if selected)
       ↓
9. Generate Cover Letter with application_id (if selected, streaming)
       ↓
10. Redirect to /tracker?new=<application_id>
```

## Entry Points

- **`/smart-apply`** — dedicated page with its own nav item
- **Tracker header** — "Smart Apply" button navigates to `/smart-apply`

## Page Layout — Four Progressive Sections

### Section 1: Job Input

- URL text field + "Analyze Job" button
- "Paste text instead" toggle for jobs without a URL
- Sections 2–4 are hidden until analysis completes

### Section 2: Job Analysis (auto-runs, read-only)

Runs immediately after URL is submitted. Scrape and fit analysis run sequentially (fit analysis needs the scraped job description). Displays:

- Fit score ring (0–100, from `match_score`)
- Pros as green cards (from `pros` field of fit response)
- Cons as red/amber cards (from `cons` field of fit response)
- Missing keywords chips (from `missing_keywords` field)
- `red_flags`, `suggested_emphasis`, and `interview_questions` are suppressed in this view to keep focus on the generation decision
- Loading skeleton while in progress

Uses existing fit analysis UI patterns from the cover letter page.

### Section 3: Job Details (editable)

After scrape completes, show two editable fields pre-filled from available data:

- **Company name** — from `company_name` in scrape response (editable, required for Application record)
- **Role title** — extracted from the job description text on the frontend using the same heuristic as the cover letter page (`extractFromTitleLine`). This field is editable and required before proceeding, since the scrape API does not return a structured `role_title` field.

### Section 4: Generate Options

Two independently toggleable cards. Both default to on.

**Generate CV card** (toggle)
- ATS Enhance toggle (default: on)
- Extra context textarea (optional)

**Generate Cover Letter card** (toggle)
- Tone picker: Professional / Enthusiastic / Concise / Creative (default: Professional)
- Extra context textarea (optional)
- Company name field (pre-filled from scrape, editable — mirrors Section 3)

If both toggles are off, the action button is disabled.

### Section 5: Generate & Track

- Single **"Generate & Track"** button
- Progress feedback: "Creating application… → Generating CV… → Generating cover letter… → Done!"
- On completion: redirect to `/tracker?new=<application_id>`

## Backend Changes (minimal)

### Backend changes (schema fields only, no new endpoints)

Three optional fields added to existing schemas:

1. `GenerateCvRequest` gains `application_id: int | None = None` and `extra_context: str | None = None`. The `extra_context` is appended to the ATS enhancement user prompt. The `application_id` is stored on the saved `GeneratedCV` row.

2. `CoverLetterRequest` gains `application_id: int | None = None` (it already has `match_score` and `extra_context`). The streaming closure in `generate_cover_letter` must be updated to write `application_id=req.application_id` when constructing the `GeneratedCoverLetter` DB row after `[DONE]`.

No new endpoints. No new DB columns (both `GeneratedCV.application_id` and `GeneratedCoverLetter.application_id` FK columns already exist).

### Correct API chaining order

```
POST /api/scrape/job
  body: { url }
  response: { job_description, company_name, source }

POST /api/analyze/fit
  body: { profile_id, job_description }
  response: { match_score, pros, cons, missing_keywords, red_flags, ... }

POST /api/applications
  body: { company_name, role_title, job_url, profile_id, status: "applied" }
  response: { id, ... }   ← application_id used in subsequent calls
  note: match_score is NOT a field on Application; it is persisted via GeneratedCoverLetter.match_score
        and resolved at read time by the tracker. Pass it in the cover letter request instead.

POST /api/generate/cv          [if CV toggled]
  body: { profile_id, enhance, job_description, application_id, extra_context? }
  note: extra_context and application_id are new optional fields added to GenerateCvRequest
  response: { enhanced, profile }

POST /api/generate/cover-letter  [if CL toggled, SSE stream]
  body: { profile_id, job_description, company_name, tone, extra_context?, application_id, match_score }
  note: application_id is a new optional field added to CoverLetterRequest
        match_score from fit analysis is passed here so it gets persisted on GeneratedCoverLetter
  stream: text chunks → [DONE]
  (backend SSE closure writes GeneratedCoverLetter row with application_id after [DONE])
```

**Application is created first** so its ID can be passed to both generators. The tracker already resolves linked documents by querying `GeneratedCV` and `GeneratedCoverLetter` by `application_id`, so no further update is needed after generation.

## State Management

All state is local to the `/smart-apply` page component:

| State | Type | Description |
|-------|------|-------------|
| `jobUrl` | string | User URL input |
| `jobText` | string | Manual paste fallback |
| `useManualText` | bool | Toggle between URL and paste mode |
| `analysisLoading` | bool | Scrape + fit in progress |
| `scrapeResult` | object \| null | `{ job_description, company_name, source }` |
| `fitResult` | object \| null | `{ match_score, pros, cons, missing_keywords, ... }` |
| `companyName` | string | Editable, pre-filled from scrapeResult |
| `roleTitle` | string | Editable, extracted from job description text |
| `generateCv` | bool | CV toggle (default: true) |
| `generateCl` | bool | Cover letter toggle (default: true) |
| `cvEnhance` | bool | ATS enhance toggle (default: true) |
| `cvContext` | string | CV extra context |
| `clTone` | string | Cover letter tone (default: "professional") |
| `clContext` | string | Cover letter extra context |
| `generating` | bool | Generation in progress |
| `generationStep` | string | UI feedback label |

## Error Handling

- Scrape fails → show error inline, reveal "paste text instead" fallback
- Fit analysis fails → show warning, allow user to continue (match_score will be null on Application)
- Application creation fails → toast error, abort generation (nothing to link to)
- CV generation fails → toast error, still attempt cover letter
- Cover letter generation fails → toast error, redirect to tracker anyway (Application exists)

## Tracker Integration

- Redirect URL: `/tracker?new=<application_id>`
- The tracker page reads `?new` query param on mount and auto-opens the detail panel / scrolls to that application card
- This is a small addition to the tracker page — read the param, find the card by ID, expand it

## Application Status

The Application record is always created with `status: "applied"`. This is intentional — Smart Apply represents the intent to apply or an active application. Users can change the status freely in the tracker afterward.

## Navigation

Nav item added alongside "Cover Letter" in the sidebar, labelled "Smart Apply" with an appropriate icon (e.g. `Zap` or `Rocket`).

## What This Is Not

- Not a one-click auto-generate with no user review (user always reviews fit and configures)
- Not a replacement for the individual CV/cover letter generators (those remain)
- Does not send applications anywhere (no ATS integration, just document + tracker)
- Does not display interview questions or suggested emphasis (available in cover letter page fit analysis)
