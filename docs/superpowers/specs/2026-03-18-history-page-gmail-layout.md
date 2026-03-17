# History Page — Gmail-Style Layout Revamp

**Date:** 2026-03-18
**Status:** Approved

## Goal

Replace the current drawer-based cover letter history layout with a permanent two-column "Gmail-style" layout: a fixed-width scrollable sidebar on the left showing rich cards, and a full-height preview panel on the right that updates as the user clicks cards.

## Scope

All changes are in `frontend/src/routes/history/+page.svelte`. No backend changes, no new files, no new components.

---

## Layout

### Overall structure

```
┌────────────────────────────────────────────────────────┐
│  History                                 [profile pills]│
│  Generated CVs (n) │ Cover Letters (n)                  │
│  ─────────────────────────────────────────────────────  │
│  [search] [match▾] [sort▾]                              │
├───────────────┬────────────────────────────────────────┤
│  sidebar      │  preview panel                          │
│  320px fixed  │  1fr, fills remaining height           │
│  scrollable   │  independently scrollable              │
└───────────────┴────────────────────────────────────────┘
```

- The two-column grid is **always active** for the cover-letter tab (no conditional switching).
- Both columns fill `calc(100vh - [header+tabs+filterbar height])` and scroll independently.
- On screens narrower than `md` (768px): sidebar stacks on top of preview. When a card is selected, sidebar hides and preview shows full-width with a **← Back** button.

---

## Left Sidebar — Card Design (Option C: Rich)

Each card shows:

1. **Row 1:** Company name (bold) + match score badge (color-coded: green ≥70, yellow 40–69, red <40)
2. **Row 2:** Role snippet (first line of job_description, max 50 chars) + date (short format: "Mar 17")
3. **Row 3:** Match score progress bar (colored by score)
4. **Row 4:** All 4 status pills — active one is filled+colored, inactive ones are ghost outlines. Tapping an inactive pill sets that status.
5. **Row 5 (conditional):** `📌 Tracked →` link if `application_id` is set

**Selected state:** `border-primary` + subtle `bg-accent` background + slight shadow.

**No checkbox** visible by default — checkboxes appear on hover/focus (or always shown, not removed).

> Note: The existing `STATUS_PIPELINE`, `scoreColor`, `scoreBarColor`, `displayRole`, `formatDateShort`, `displayCompany` helpers are already in the file and must be reused.

---

## Right Preview Panel — Design (Option C: Rich Header)

### When nothing is selected (empty state)

Centered content in the panel:
```
📄
Select a cover letter to preview
Click any card on the left
```

### When a card is selected

**Section 1 — Gradient header**
- Background: `linear-gradient(135deg, indigo-50, green-50)` (light, subtle)
- Left: circular match score gauge (conic-gradient ring, white inner circle showing score %)
- Center: company name (large, bold) + role snippet + date below it + status pill + tracker link
- Right: Copy, Print, Delete buttons (horizontal row)

**Section 2 — Tab bar** (only shown when `fit_analysis` is present)
- `📄 Cover Letter` | `📊 Fit Analysis`
- Active tab has `border-b-2 border-primary`

**Section 3 — Scrollable content**
- Cover Letter tab: `<CoverLetterPreview>` component
- Fit Analysis tab: existing analysis layout (match bar, strengths/gaps grid, missing keywords, red flags, suggested emphasis, interview questions)

---

## Height / Scroll Behaviour

The outer page wrapper `<div class="space-y-6">` grows naturally. The two-column section needs a **fixed height** so both columns scroll independently without the whole page scrolling past the panel.

Use `h-[calc(100vh-220px)]` (approximate; tuned to leave room for header, tabs, filter bar) on the grid container, with `overflow-hidden` on the grid and `overflow-y-auto` on each column.

---

## Mobile Behaviour (< md)

- Grid is single column (`grid-cols-1`)
- When `selectedCl` is null: sidebar shown full-width
- When `selectedCl` is set: sidebar hidden (`hidden`), preview shown full-width with **← Back** button in header

---

## Removed / Unchanged

- **Removed:** Drawer (`fixed` right-side panel + backdrop overlay)
- **Removed:** `hidden md:block` conditional on sidebar
- **Unchanged:** Filter bar (search, match filter, sort), bulk delete UI, CV tab (untouched)
- **Unchanged:** All helper functions and state already added in prior commits

---

## Key Constraints

- No nested `<button>` inside `<button>` — status pills inside the card button must use `<span role="button" tabindex="0">` (already done in current code)
- Clicking a status pill must call `e.stopPropagation()` to prevent card selection
- The `previewTab` reset effect (`if (selectedCl) previewTab = 'letter'`) is already in place
