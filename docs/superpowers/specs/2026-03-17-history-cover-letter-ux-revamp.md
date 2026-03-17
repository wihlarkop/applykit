# History Cover Letter UX Revamp — Design Spec

## Goal

Revamp the cover letter history page to be more information-dense, actionable, and user-friendly — richer list cards, inline status pipeline, and a tabbed preview pane with fit analysis.

## Architecture

Pure frontend change. No backend modifications needed — all data (`match_score`, `fit_analysis`, `tone`, `application_status`, `application_id`) is already returned by `GET /api/history/cover-letter`. Changes are confined to `frontend/src/routes/history/+page.svelte`.

## Data Types (reference)

`GeneratedCoverLetterEntry` fields used:
- `company_name: string | null` — may be null; `displayCompany()` helper provides fallback
- `job_description: string` — full JD text; first line used as role snippet when no company_name
- `match_score: number | null`
- `tone: string` — default "professional"
- `application_status: string | null` — one of: applied, interviewing, offer, rejected, or null
- `application_id: number | null`
- `fit_analysis: FitAnalysisResponse | null`

`FitAnalysisResponse` fields:
- `match_score: number`
- `pros: string[]`
- `cons: string[]`
- `missing_keywords: string[]`
- `red_flags: string[]`
- `suggested_emphasis: string` — single paragraph string
- `interview_questions: string[]`

---

## 1. Card Redesign (Inline Status Pipeline)

Replace the current narrow card (company + dropdown) with a richer card:

### Layout
```
┌──────────────────────────────────────────────────────┐
│  Cloudera                    [87%] [casual] [● 💼]   │
│  Backend Engineer, Tech Lead              Mar 16      │
│  ████████████████████░░░  87%                        │
│  [ Applied ]  [ Interviewing ✓ ]  [ Offer ]  [ Rejected ] │
└──────────────────────────────────────────────────────┘
```

### Card structure
- **Row 1**: Company name (bold, `displayCompany()`) + match score badge + tone badge (only if `tone !== 'professional'`) + profile dot+icon (only if `entry.profile_color && entry.profile_icon` — same pattern as existing card code) (right-aligned cluster)
- **Row 2**: JD role snippet (muted, small) + date (right-aligned)
- **Row 3**: Match score bar (only if `match_score !== null`)
- **Row 4**: Status pipeline pills + Tracked badge (only if `application_id` is set)

### Role snippet (Row 2)
`GeneratedCoverLetterEntry` has no `role_title` field. Use the first line of `job_description`, trimmed, max 50 chars with `…` if longer. If empty, show nothing (the row is omitted). Helper:
```ts
function displayRole(entry: GeneratedCoverLetterEntry): string {
  const firstLine = entry.job_description.split('\n')[0].trim();
  if (!firstLine) return '';
  return firstLine.length > 50 ? firstLine.slice(0, 47) + '…' : firstLine;
}
```
Row 2 role snippet is only rendered when `displayRole(entry)` returns a non-empty string.

### Match score bar (Row 3)
- `<div>` with `bg-muted` background, inner div with width `${match_score}%`
- Color: green ≥70, amber 40–69, red <40 (same as badge)
- Height: `h-1` (4px), `rounded-full`
- Omit entirely when `match_score` is null

### Status pipeline pills (Row 4)
Four pill buttons: Applied · Interviewing · Offer · Rejected.

**Active pill** (matches `entry.application_status`):
- Filled background colored by status: applied=blue, interviewing=amber, offer=green, rejected=red
- Not clickable (no onclick)

**Inactive pills**:
- Ghost style: `border border-border text-muted-foreground`
- On click: call `handleClStatusChange(entry.id, status)` — no optimistic update, pills reflect server response only (matching existing pattern)

**When `application_status` is null**: all 4 pills are ghost/inactive. Clicking any calls `handleClStatusChange(entry.id, status)`. The backend's `PATCH /history/cover-letter/{id}/status` endpoint auto-creates an Application record when transitioning from null to a status — no separate API call needed from the frontend.

**Tracked badge**: shown only when `entry.application_id !== null`. Renders as `<a href="/tracker">📌 Tracked →</a>` inline after the pill row.

### Checkbox for bulk delete
Keep the existing checkbox to the left of each card (unchanged behavior).

---

## 2. Preview Pane Header (Two-Row)

Replace the current single-row header with a two-row header:

### Row 1 — Identity + Actions
```
Cloudera  Backend Engineer, Tech Lead     [Copy] [Print] [Delete]
```
- Company: `displayCompany(selectedCl)`, bold
- Role snippet: `displayRole(selectedCl)`, muted, inline after company
- Action buttons: Copy, Print, Delete (unchanged)

### Row 2 — Metadata Strip
```
[87% match]  [casual]  [● Interviewing]  [📌 Tracker →]     Mar 16, 5:34 PM
```
- Match score badge: same color scheme, only if `match_score !== null`
- Tone badge: only if `tone !== 'professional'` (consistent with card)
- Status pill: purely **decorative/read-only, no click handler**. Colored by status. Only if `application_status !== null`.
- Tracker link: `<a href="/tracker">📌 Tracker →</a>`. Only if `application_id !== null`.
- Date: right-aligned, `formatDate(selectedCl.created_at)`

---

## 3. Preview Pane Tabs

Add a tab bar immediately below the two-row header.

### Tab state
- New state variable: `let previewTab = $state<'letter' | 'analysis'>('letter')`
- **Reset to `'letter'` whenever `selectedCl` changes** — implement via `$effect(() => { if (selectedCl) previewTab = 'letter'; })`

### Tab bar
Two tabs: `📄 Cover Letter` | `📊 Fit Analysis`

The Fit Analysis tab is **hidden** (not rendered) when `selectedCl.fit_analysis` is null. When hidden, only the Cover Letter tab is shown (no tab bar needed — just render content directly).

### Tab 1 — Cover Letter (default)
Unchanged: `<CoverLetterPreview text={selectedCl.cover_letter_text} />`

### Tab 2 — Fit Analysis
Only rendered when `selectedCl.fit_analysis` is non-null. Layout:

1. **Match score bar** — label "Match Score", percentage right, full-width bar (same as card but taller: `h-2`)

2. **Strengths / Gaps — 2-column grid**
   - Strengths (green): render `fit_analysis.pros` as bullet list. Section hidden if `pros` is empty.
   - Gaps (red): render `fit_analysis.cons` as bullet list. Section hidden if `cons` is empty.

3. **Missing Keywords** — `fit_analysis.missing_keywords` as flex-wrap pill list. Section hidden if empty.

4. **Red Flags** — `fit_analysis.red_flags` as bullet list with warning color. Section hidden if empty.

5. **Suggested Emphasis** — `fit_analysis.suggested_emphasis` as a paragraph (`<p>`). Section hidden if empty string.

6. **Interview Questions** — `fit_analysis.interview_questions` as a numbered list (`<ol>`). Section hidden if empty.

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
