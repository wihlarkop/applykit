# Application Tracker — Design Spec

**Date:** 2026-03-16
**Status:** Approved for implementation

## Overview

A dedicated `/tracker` page with a Kanban board for managing job applications across four stages: Applied → Interviewing → Offer → Rejected. Applications are a first-class entity — they exist independently of generated documents. Cover letters and CVs optionally link to an application via a nullable FK.

---

## Architecture

### New Backend Endpoints

```
POST   /api/applications
GET    /api/applications
GET    /api/applications/{id}
PATCH  /api/applications/{id}
DELETE /api/applications/{id}
```

### Modified Endpoints

```
POST /api/generate/cover-letter   ← add optional application_id + tracker creation
```

### New DB Table: `application`

```sql
id            INTEGER   PRIMARY KEY AUTOINCREMENT
company_name  TEXT      NOT NULL
role_title    TEXT      NOT NULL
status        TEXT      NOT NULL  DEFAULT 'applied'
job_url       TEXT      NULL
notes         TEXT      NULL
applied_date  DATE      NULL
profile_id    INTEGER   NULL  REFERENCES profile(id) ON DELETE SET NULL
created_at    DATETIME  NOT NULL  DEFAULT CURRENT_TIMESTAMP
updated_at    DATETIME  NOT NULL  DEFAULT CURRENT_TIMESTAMP
```

`status` valid values (enforced in Pydantic): `applied | interviewing | offer | rejected`

### Modified DB Tables

```
generated_cover_letter  ← add application_id INTEGER NULL REFERENCES application(id) ON DELETE SET NULL
generated_cv            ← add application_id INTEGER NULL REFERENCES application(id) ON DELETE SET NULL
```

Deleting an application sets `application_id = NULL` on all linked documents — no cascade delete.

---

## Section 1: Tracker Page UI (`/tracker`)

### Filter Bar

```
[🔍 Search company or role...]  [Profile ▾]  [This month ▾]  [Match ▾]
```

- **Search**: debounced 300ms → server-side, searches `company_name + role_title`
- **Profile**: filter by profile_id
- **Date range**: `All time | This week | This month | Last 3 months` — filters by `applied_date`
- **Match score**: `All | High (≥70%) | Medium (40–69%) | Low (<40%)` — filters applications that have a linked cover letter with a match_score

All filters are server-side query params on `GET /api/applications`.

### Kanban Board

Four fixed-height columns with independent vertical scroll:

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ APPLIED   47 │  │INTERVIEWING 8│  │  OFFER     2 │  │ REJECTED  43 │
│──────────────│  │──────────────│  │──────────────│  │──────────────│
│ [Card]       │  │ [Card]       │  │ [Card]       │  │ [Card]       │
│ [Card]       │  │ [Card]       │  │              │  │ [Card]  ↓    │
│ [Card]  ↕    │  │              │  │ Drop here    │  │ scrollable   │
│ scrollable   │  │              │  │              │  │              │
│──────────────│  │──────────────│  │──────────────│  │──────────────│
│ + Add        │  │ + Add        │  │ + Add        │  │ + Add        │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

Column header colors: Applied = muted, Interviewing = amber, Offer = green, Rejected = red.

### Application Card

```
┌─────────────────────────────────────┐
│ ● Acme Corp                         │
│   Senior Engineer                   │
│   Mar 14        [78%] [CL]          │
└─────────────────────────────────────┘
```

- Profile color dot (left)
- Company name (bold)
- Role title
- Applied date + badges: match score (green ≥70%, yellow 40–69%, red <40%, absent if no fit analysis), `CL` if cover letter linked, `CV` if CV linked
- Dashed border + "no docs linked" if no cover letter or CV is attached
- Cards without a linked cover letter (no match score) show no match badge

### Card Interactions

- **Drag and drop**: drag card to another column → `PATCH /api/applications/{id}` with new status. Uses `@dnd-kit/core`.
- **Status dropdown**: small dropdown on each card as fallback for status change → same PATCH call
- **Click card**: opens detail panel

### Detail Panel

Slides in from the right when a card is clicked. Does not navigate away from the board.

```
┌─────────────────────────────────┐
│ Acme Corp — Senior Engineer   ✕ │
├─────────────────────────────────┤
│ Status:  [Interviewing ▾]       │
│ Applied: Mar 14, 2026           │
│ URL:     https://...            │
├─────────────────────────────────┤
│ Notes                           │
│ ┌─────────────────────────────┐ │
│ │ Textarea (editable)         │ │
│ └─────────────────────────────┘ │
│                      [Save]     │
├─────────────────────────────────┤
│ Linked Documents                │
│ 📄 Cover Letter — Mar 14  [View]│
│ 📋 CV — Mar 14            [View]│
├─────────────────────────────────┤
│             [Delete Application]│
└─────────────────────────────────┘
```

- Status dropdown in panel also calls `PATCH /api/applications/{id}`
- Notes textarea: auto-saves on blur or via Save button → `PATCH /api/applications/{id}`
- Linked document rows link to the respective history detail view
- Delete prompts a confirmation dialog; on confirm calls `DELETE /api/applications/{id}`

### Add Application (inline)

`+ Add application` at the bottom of each column opens a mini inline form within that column:

```
Company name*  [________________]
Role title*    [________________]
Job URL        [________________]
Applied date   [Today ▾        ]
               [Cancel]  [Add →]
```

Status is pre-filled to the column the user clicked. Profile defaults to the active profile. `POST /api/applications` on submit.

---

## Section 2: Backend

### Schemas

```python
class ApplicationStatus(str, Enum):
    applied      = "applied"
    interviewing = "interviewing"
    offer        = "offer"
    rejected     = "rejected"

class CreateApplicationRequest(BaseModel):
    company_name: str
    role_title: str
    status: ApplicationStatus = ApplicationStatus.applied
    job_url: str | None = None
    notes: str | None = None
    applied_date: date | None = None
    profile_id: int | None = None

class UpdateApplicationRequest(BaseModel):
    company_name: str | None = None
    role_title: str | None = None
    status: ApplicationStatus | None = None
    job_url: str | None = None
    notes: str | None = None
    applied_date: date | None = None

class LinkedDoc(BaseModel):
    id: int
    created_at: datetime
    type: Literal["cover_letter", "cv"]

class ApplicationEntry(BaseModel):
    id: int
    company_name: str
    role_title: str
    status: str
    job_url: str | None
    notes: str | None
    applied_date: date | None
    created_at: datetime
    profile_id: int | None
    profile_label: str | None
    profile_color: str | None
    profile_icon: str | None
    match_score: int | None          # from linked cover letter, NULL if none or skipped
    linked_cover_letter_id: int | None
    linked_cv_id: int | None

class ApplicationListResponse(BaseModel):
    items: list[ApplicationEntry]
    total: int
```

### `GET /api/applications` Query Params

```
profile_id:   int | None
status:       str | None
search:       str | None      (searches company_name + role_title)
date_from:    date | None
date_to:      date | None
sort:         "date_desc" | "date_asc"   default: date_desc
```

Returns all matching applications (no pagination) — Kanban drag-and-drop requires full column data client-side.

`match_score` on `ApplicationEntry` is read from the most recently linked `generated_cover_letter` row where `match_score IS NOT NULL`.

### Cover Letter Generation Change

`CoverLetterRequest` gains two optional fields:

```python
application_id: int | None = None    # link to existing application
add_to_tracker: bool = False         # create new application on generation
tracker_role_title: str | None = None  # required if add_to_tracker=True and role not inferable
```

If `add_to_tracker=True`:
1. Backend creates an `Application` record using `company_name` from the request, `tracker_role_title`, `job_url`, and today's date as `applied_date`
2. Links the generated cover letter to the new application via `application_id`
3. Returns `application_id` in the cover letter response

If `application_id` is provided directly, skips creation and links to the existing application.

### `DELETE /api/applications/{id}`

Sets `application_id = NULL` on all linked `generated_cover_letter` and `generated_cv` rows before deleting the application record.

---

## Section 3: Cover Letter Page UI Changes

### Tracker Checkbox

Appears between the tone selector and the Generate button:

```
┌────────────────────────────────────────┐
│ ☑  Track this application             │
│    Role title  [________________]      │  ← shown when checked
│    Applied     [Mar 16, 2026    ]      │  ← shown when checked, defaults to today
└────────────────────────────────────────┘
```

- Checkbox is unchecked by default
- When checked: role title input and applied date field expand (animate in)
- Role title: autofilled if URL was scraped from Greenhouse or Lever (API returns job title); blank otherwise
- Applied date: defaults to today
- Fields are optional for the checkbox — role_title is required but user can type it; applied_date has a default

---

## Section 4: Navigation

Add `Tracker` to the sidebar nav between `History` and `Settings`:

```
Dashboard
Generate CV
Cover Letter
History
Tracker       ← new
Settings
```

---

## Data Flow Summary

```
User adds application manually
  → POST /api/applications (company, role, status, date)
  → card appears in correct Kanban column

User generates cover letter with "Track this application" checked
  → POST /api/generate/cover-letter (add_to_tracker=true, tracker_role_title, ...)
  → backend creates Application + links cover letter
  → card appears in Applied column

User drags card to Interviewing
  → PATCH /api/applications/{id} { status: "interviewing" }
  → card moves column

User opens card detail
  → GET /api/applications/{id}
  → sees notes, linked docs, match score
  → edits notes → PATCH on blur

User filters by "This month" + "High match"
  → GET /api/applications?date_from=2026-03-01&date_to=2026-03-31 (match_min handled client-side from returned match_score)
```

---

## Files to Create / Modify

| File | Action |
|------|--------|
| `backend/app/routes/applications.py` | Create — CRUD for applications |
| `backend/app/schemas.py` | Modify — new Application schemas |
| `backend/app/models.py` | Modify — Application model + FK columns on cover letter + CV |
| `backend/migrations/` | Create — Alembic migration |
| `backend/main.py` | Modify — register applications router |
| `frontend/src/routes/tracker/+page.svelte` | Create — Kanban board |
| `frontend/src/routes/cover-letter/+page.svelte` | Modify — tracker checkbox |
| `frontend/src/lib/api.ts` | Modify — application API functions |
| `frontend/src/lib/types.ts` | Modify — Application types |
| `frontend/src/routes/+layout.svelte` | Modify — add Tracker nav link |

---

## Out of Scope (Future)

- Bulk delete applications
- Application notes history / changelog
- Deadline reminders or calendar sync
- Export applications to CSV
- Email tracking integration (detect replies in Gmail)
