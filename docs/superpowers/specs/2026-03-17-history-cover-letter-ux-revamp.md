# History Cover Letter UX Revamp — Design Spec

## Goal

Revamp the cover letter history page to be more information-dense, actionable, and user-friendly — richer list cards, inline status pipeline, and a tabbed preview pane with fit analysis.

## Architecture

Pure frontend change. No backend modifications needed — all data (`match_score`, `fit_analysis`, `tone`, `application_status`, `application_id`) is already returned by `GET /api/history/cover-letter`. Changes are confined to `frontend/src/routes/history/+page.svelte`.

---

## 1. Card Redesign (Option B — Inline Status Pipeline)

Replace the current narrow card (company + dropdown) with a richer card:

### Layout
```
┌─────────────────────────────────────────────┐
│  Cloudera                            [87%] [casual] [● •] │
│  Backend Engineer, Tech Lead                 Mar 16        │
│  ████████████████████░░░░  87%               │
│  [Applied] [Interviewing ✓] [Offer] [Rejected]            │
└─────────────────────────────────────────────┘
```

### Specs
- **Company name**: Bold, large — use `displayCompany()` (already handles null gracefully)
- **Role/JD snippet**: Small muted text below company (first 50 chars of job description if no role title)
- **Match score badge**: Colored pill inline (green ≥70, amber 40–69, red <40) — top right
- **Tone badge**: Show only if not `professional` (same as current)
- **Profile dot**: Small colored dot + icon — top right cluster
- **Match score bar**: Thin horizontal progress bar (3px height) below the role text, colored by score
- **Status pipeline**: 4 pill buttons in a row — `Applied | Interviewing | Offer | Rejected`. Active pill is filled/colored, inactive pills are ghost. Clicking an inactive pill calls `handleClStatusChange`. Active pill is not clickable (already set).
- **Status colors**: applied=blue, interviewing=amber, offer=green, rejected=red
- **Tracked badge**: `📌 Tracked →` link to `/tracker` shown when `entry.application_id` is set, inline after the pipeline
- **No match score bar** when `match_score` is null

### Status pipeline interaction
- If `application_status` is null: all 4 pills are ghost/inactive, clicking any sets the status + auto-creates Application (existing backend behavior)
- If status is set: that pill is active/filled, others are ghost. Clicking a different ghost pill updates the status.
- No `—` option in the pipeline (once tracked, managed from Tracker)

### Checkbox for bulk delete
Keep the existing checkbox to the left of each card (unchanged behavior).

---

## 2. Preview Pane Header (Two-Row)

Replace the current single-row header with a two-row header:

### Row 1 — Identity + Actions
```
Cloudera  Backend Engineer, Tech Lead     [Copy] [Print] [Delete]
```
- Company name bold, role/JD snippet muted inline
- Action buttons right-aligned (unchanged)

### Row 2 — Metadata Strip
```
[87% match] [casual] [● Interviewing] [📌 Tracker →]        Mar 16, 5:34 PM
```
- Match score badge (colored, same scheme as card)
- Tone badge (only if not `professional`)
- Status pill (read-only display of current status, colored)
- Tracker link (only if `application_id` is set)
- Date right-aligned

---

## 3. Preview Pane Tabs

Add a tab bar below the two-row header with two tabs:

### Tab 1 — Cover Letter (default active)
- Unchanged: renders `<CoverLetterPreview text={...} />`

### Tab 2 — Fit Analysis
Only shown when `selectedCl.fit_analysis` is non-null. If null, tab is disabled/hidden.

Layout of analysis tab:
1. **Match score bar** — label "Match Score", percentage right, full-width progress bar (6px, colored gradient)
2. **Strengths / Gaps grid** — 2-column grid
   - Strengths (green border): list of `fit_analysis.pros`
   - Gaps (red border): list of `fit_analysis.cons`
3. **Matched Keywords** — flex-wrap pill list from `fit_analysis.keywords`
4. **Red Flags** — if `fit_analysis.red_flags` is non-empty, show a warning section
5. **Suggested Emphasis** — if present, bullet list of `fit_analysis.suggested_emphasis`
6. **Interview Prep** — if `fit_analysis.interview_prep` is non-empty, numbered list

All sections are shown only if the data is present (graceful null handling).

---

## 4. Company Name Fix

The current `displayCompany()` function already handles null by falling back to a JD snippet. No change needed — the new card layout just uses it more prominently.

---

## Files

- **Modify only**: `frontend/src/routes/history/+page.svelte`

No new components, no backend changes.

---

## Non-Goals

- No changes to the CV tab
- No changes to filters/sort/bulk delete behavior
- No backend changes
- No new files
