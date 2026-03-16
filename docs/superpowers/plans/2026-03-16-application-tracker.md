# Application Tracker Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/tracker` Kanban page for managing job applications across Applied → Interviewing → Offer → Rejected, with cover letter generation optionally linking to a tracked application.

**Architecture:** New `Application` SQLAlchemy model with nullable FKs on existing `generated_cover_letter` and `generated_cv` tables. New FastAPI router at `/api/applications`. SvelteKit `/tracker` page with `svelte-dnd-action` for drag-and-drop.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, SvelteKit (Svelte 5 runes), `svelte-dnd-action`, Tailwind CSS 4

---

## Chunk 1: Backend

### Task 1: DB Model + Migration

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/migrations/versions/<hash>_add_application_tracker.py`

- [ ] **Step 1: Add `Application` model and FK columns to `models.py`**

Add `Date` to sqlalchemy imports. Add the new model and two new columns at the bottom of the file:

```python
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
```

Add after `GeneratedCoverLetter`:

```python
class Application(Base):
    __tablename__ = "application"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False)
    role_title = Column(String, nullable=False, default="")
    status = Column(String, nullable=False, default="applied")
    job_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    applied_date = Column(Date, nullable=True)
    profile_id = Column(
        Integer, ForeignKey("profile.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
```

Add `application_id` FK to `GeneratedCV` and `GeneratedCoverLetter`:

```python
# In GeneratedCV, after profile_id:
application_id = Column(
    Integer, ForeignKey("application.id", ondelete="SET NULL"), nullable=True
)

# In GeneratedCoverLetter, after profile_id:
application_id = Column(
    Integer, ForeignKey("application.id", ondelete="SET NULL"), nullable=True
)
```

- [ ] **Step 2: Generate Alembic migration**

```bash
cd backend
uv run alembic revision --autogenerate -m "add_application_tracker"
```

Expected: new file created in `backend/migrations/versions/`.

- [ ] **Step 3: Verify migration content**

Open the generated migration file. Confirm it contains:
- `op.create_table('application', ...)` with all columns
- `op.add_column('generated_cv', sa.Column('application_id', ...))`
- `op.add_column('generated_cover_letter', sa.Column('application_id', ...))`

If autogenerate missed any column, add it manually.

- [ ] **Step 4: Apply migration**

```bash
cd backend
uv run alembic upgrade head
```

Expected: `Running upgrade ... -> <hash>, add_application_tracker`

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/models.py backend/migrations/
rtk git commit -m "feat: add Application model and FK columns for tracker"
```

---

### Task 2: Application Schemas

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Add imports and Application schemas**

Add `date` to datetime import at top of `schemas.py`:

```python
from datetime import date, datetime
```

Add at the bottom of `schemas.py`:

```python
# --- Application Tracker schemas ---


class ApplicationStatus(str, Enum):
    applied = "applied"
    interviewing = "interviewing"
    offer = "offer"
    rejected = "rejected"


class CreateApplicationRequest(BaseModel):
    company_name: str
    role_title: str = ""
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


class ApplicationEntry(BaseModel):
    id: int
    company_name: str
    role_title: str
    status: ApplicationStatus
    job_url: str | None
    notes: str | None
    applied_date: date | None
    created_at: datetime
    profile_id: int | None
    profile_label: str | None
    profile_color: str | None
    profile_icon: str | None
    match_score: int | None
    linked_cover_letter_id: int | None
    linked_cv_id: int | None

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    items: list[ApplicationEntry]
    total: int
```

Also add `Enum` to imports:

```python
from enum import Enum
```

- [ ] **Step 2: Commit**

```bash
rtk git add backend/app/schemas.py
rtk git commit -m "feat: add Application schemas"
```

---

### Task 3: Applications Route

**Files:**
- Create: `backend/app/routes/applications.py`

- [ ] **Step 1: Create the route file**

```python
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, GeneratedCoverLetter, GeneratedCV, Profile
from app.schemas import (
    ApplicationEntry,
    ApplicationListResponse,
    ApplicationStatus,
    CreateApplicationRequest,
    UpdateApplicationRequest,
)

router = APIRouter()


def _enrich_app(app: Application, profiles: dict) -> dict:
    """Build ApplicationEntry dict from ORM object + profile map.
    match_score, linked_cover_letter_id, linked_cv_id are filled in
    by the caller after running _resolve_docs()."""
    p = profiles.get(app.profile_id) if app.profile_id else None
    return {
        "id": app.id,
        "company_name": app.company_name,
        "role_title": app.role_title,
        "status": app.status,
        "job_url": app.job_url,
        "notes": app.notes,
        "applied_date": app.applied_date,
        "created_at": app.created_at,
        "profile_id": app.profile_id,
        "profile_label": p.label if p else None,
        "profile_color": p.color if p else None,
        "profile_icon": p.icon if p else None,
        "match_score": None,  # filled in by _resolve_scores()
        "linked_cover_letter_id": None,  # filled in by _resolve_docs()
        "linked_cv_id": None,  # filled in by _resolve_docs()
    }


def _profile_map(apps: list[Application], db: Session) -> dict:
    ids = {a.profile_id for a in apps if a.profile_id}
    if not ids:
        return {}
    return {p.id: p for p in db.query(Profile).filter(Profile.id.in_(ids)).all()}


def _resolve_docs(app_ids: list[int], db: Session) -> tuple[dict, dict, dict]:
    """
    Returns three dicts keyed by application_id:
      - cl_id: most recent cover letter id per application
      - cv_id: most recent cv id per application
      - match_score: match_score from most recent cover letter with a score
    """
    if not app_ids:
        return {}, {}, {}

    cls = (
        db.query(GeneratedCoverLetter)
        .filter(GeneratedCoverLetter.application_id.in_(app_ids))
        .order_by(GeneratedCoverLetter.created_at.desc())
        .all()
    )
    cvs = (
        db.query(GeneratedCV)
        .filter(GeneratedCV.application_id.in_(app_ids))
        .order_by(GeneratedCV.created_at.desc())
        .all()
    )

    cl_id: dict = {}
    match_scores: dict = {}
    for cl in cls:
        aid = cl.application_id
        if aid not in cl_id:
            cl_id[aid] = cl.id
        score = getattr(cl, "match_score", None)
        if aid not in match_scores and score is not None:
            match_scores[aid] = score

    cv_id: dict = {}
    for cv in cvs:
        aid = cv.application_id
        if aid not in cv_id:
            cv_id[aid] = cv.id

    return cl_id, cv_id, match_scores


# --- Endpoints ---


@router.post("/applications", response_model=ApplicationEntry)
def create_application(
    body: CreateApplicationRequest, db: Session = Depends(get_db)
):
    app = Application(
        company_name=body.company_name,
        role_title=body.role_title,
        status=body.status.value,
        job_url=body.job_url,
        notes=body.notes,
        applied_date=body.applied_date or date.today(),
        profile_id=body.profile_id,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    pm = _profile_map([app], db)
    entry = _enrich_app(app, pm)
    cl_id, cv_id, scores = _resolve_docs([app.id], db)
    entry["linked_cover_letter_id"] = cl_id.get(app.id)
    entry["linked_cv_id"] = cv_id.get(app.id)
    entry["match_score"] = scores.get(app.id)
    return ApplicationEntry(**entry)


@router.get("/applications", response_model=ApplicationListResponse)
def list_applications(
    db: Session = Depends(get_db),
    profile_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    match_min: int | None = Query(default=None),
    match_max: int | None = Query(default=None),
    sort: str = Query(default="date_desc"),
):
    q = db.query(Application)
    if profile_id is not None:
        q = q.filter(Application.profile_id == profile_id)
    if status:
        q = q.filter(Application.status == status)
    if search:
        term = f"%{search}%"
        q = q.filter(
            Application.company_name.ilike(term) | Application.role_title.ilike(term)
        )
    if date_from:
        q = q.filter(Application.applied_date >= date_from)
    if date_to:
        q = q.filter(Application.applied_date <= date_to)
    if sort == "date_asc":
        q = q.order_by(Application.applied_date.asc().nullslast(), Application.created_at.asc())
    else:
        q = q.order_by(Application.applied_date.desc().nullslast(), Application.created_at.desc())

    apps = q.all()
    pm = _profile_map(apps, db)
    app_ids = [a.id for a in apps]
    cl_id, cv_id, scores = _resolve_docs(app_ids, db)

    items = []
    for a in apps:
        entry = _enrich_app(a, pm)
        entry["linked_cover_letter_id"] = cl_id.get(a.id)
        entry["linked_cv_id"] = cv_id.get(a.id)
        entry["match_score"] = scores.get(a.id)

        # Apply match_min / match_max filter (post-query since score is derived)
        score = entry["match_score"]
        if match_min is not None and (score is None or score < match_min):
            continue
        if match_max is not None and (score is None or score > match_max):
            continue

        items.append(ApplicationEntry(**entry))

    return ApplicationListResponse(items=items, total=len(items))


@router.get("/applications/{app_id}", response_model=ApplicationEntry)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    pm = _profile_map([app], db)
    entry = _enrich_app(app, pm)
    cl_id, cv_id, scores = _resolve_docs([app.id], db)
    entry["linked_cover_letter_id"] = cl_id.get(app.id)
    entry["linked_cv_id"] = cv_id.get(app.id)
    entry["match_score"] = scores.get(app.id)
    return ApplicationEntry(**entry)


@router.patch("/applications/{app_id}", response_model=ApplicationEntry)
def update_application(
    app_id: int, body: UpdateApplicationRequest, db: Session = Depends(get_db)
):
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "status" and value is not None:
            value = value if isinstance(value, str) else value.value
        setattr(app, field, value)
    app.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(app)
    pm = _profile_map([app], db)
    entry = _enrich_app(app, pm)
    cl_id, cv_id, scores = _resolve_docs([app.id], db)
    entry["linked_cover_letter_id"] = cl_id.get(app.id)
    entry["linked_cv_id"] = cv_id.get(app.id)
    entry["match_score"] = scores.get(app.id)
    return ApplicationEntry(**entry)


@router.delete("/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    # Nullify FKs on linked documents before deleting
    db.query(GeneratedCoverLetter).filter_by(application_id=app_id).update(
        {"application_id": None}
    )
    db.query(GeneratedCV).filter_by(application_id=app_id).update(
        {"application_id": None}
    )
    db.delete(app)
    db.commit()
    return {"deleted": 1}
```

- [ ] **Step 2: Register router in `backend/main.py`**

In the existing `from app.routes import ...` line, add `applications`:
```python
from app.routes import applications, generate, history, import_cv, profile, profiles, settings
```

Then add after the last `app.include_router(...)` call:
```python
app.include_router(applications.router, prefix="/api")
```

- [ ] **Step 3: Verify the API starts**

```bash
cd backend && uv run uvicorn main:app --reload
```

Expected: server starts, no import errors. Check `http://localhost:8000/docs` — `/api/applications` endpoints visible.

- [ ] **Step 4: Commit**

```bash
rtk git add backend/app/routes/applications.py backend/main.py
rtk git commit -m "feat: add applications CRUD route"
```

---

## Chunk 2: Frontend

### Task 4: Types and API Functions

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add Application types to `types.ts`**

```typescript
// Application Tracker
export type ApplicationStatus = 'applied' | 'interviewing' | 'offer' | 'rejected';

export interface ApplicationEntry {
  id: number;
  company_name: string;
  role_title: string;
  status: ApplicationStatus;
  job_url: string | null;
  notes: string | null;
  applied_date: string | null;  // ISO date string
  created_at: string;
  profile_id: number | null;
  profile_label: string | null;
  profile_color: string | null;
  profile_icon: string | null;
  match_score: number | null;
  linked_cover_letter_id: number | null;
  linked_cv_id: number | null;
}

export interface ApplicationListResponse {
  items: ApplicationEntry[];
  total: number;
}

export interface CreateApplicationRequest {
  company_name: string;
  role_title?: string;
  status?: ApplicationStatus;
  job_url?: string | null;
  notes?: string | null;
  applied_date?: string | null;
  profile_id?: number | null;
}

export interface UpdateApplicationRequest {
  company_name?: string;
  role_title?: string;
  status?: ApplicationStatus;
  job_url?: string | null;
  notes?: string | null;
  applied_date?: string | null;
}
```

- [ ] **Step 2: Add API functions to `api.ts`**

Add imports for new types at top:
```typescript
import type {
  ApplicationEntry,
  ApplicationListResponse,
  CreateApplicationRequest,
  UpdateApplicationRequest,
  // ... existing imports
} from './types';
```

Add at the bottom of `api.ts`:

```typescript
// Applications
export interface ApplicationFilters {
  profile_id?: number;
  status?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  match_min?: number;
  match_max?: number;
  sort?: 'date_desc' | 'date_asc';
}

export const listApplications = (filters: ApplicationFilters = {}) => {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null) params.set(k, String(v));
  }
  const qs = params.toString();
  return request<ApplicationListResponse>(`/applications${qs ? `?${qs}` : ''}`);
};

export const createApplication = (data: CreateApplicationRequest) =>
  request<ApplicationEntry>('/applications', { method: 'POST', body: JSON.stringify(data) });

export const getApplication = (id: number) =>
  request<ApplicationEntry>(`/applications/${id}`);

export const updateApplication = (id: number, data: UpdateApplicationRequest) =>
  request<ApplicationEntry>(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify(data) });

export const deleteApplication = (id: number) =>
  request<{ deleted: number }>(`/applications/${id}`, { method: 'DELETE' });
```

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/lib/types.ts frontend/src/lib/api.ts
rtk git commit -m "feat: add Application types and API functions"
```

---

### Task 5: Install svelte-dnd-action

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install the library**

```bash
cd frontend && bun add svelte-dnd-action
```

Expected: `svelte-dnd-action` added to `dependencies` in `package.json`.

- [ ] **Step 2: Commit**

```bash
rtk git add frontend/package.json frontend/bun.lock
rtk git commit -m "chore: add svelte-dnd-action for kanban drag-and-drop"
```

---

### Task 6: Application Card Component

**Files:**
- Create: `frontend/src/lib/components/tracker/ApplicationCard.svelte`

- [ ] **Step 1: Create the card component**

```svelte
<script lang="ts">
  import type { ApplicationEntry } from '$lib/types';

  let { app, onclick }: { app: ApplicationEntry; onclick: () => void } = $props();

  const matchColor = $derived(
    app.match_score === null
      ? null
      : app.match_score >= 70
        ? 'text-green-500 bg-green-500/10'
        : app.match_score >= 40
          ? 'text-yellow-500 bg-yellow-500/10'
          : 'text-red-500 bg-red-500/10'
  );

  const formatDate = (d: string | null) =>
    d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : null;
</script>

<button
  type="button"
  onclick={onclick}
  class="w-full text-left bg-card border border-border rounded-lg p-3 cursor-pointer hover:border-primary/50 transition-colors group"
  class:border-dashed={!app.linked_cover_letter_id && !app.linked_cv_id}
>
  <div class="flex items-center gap-2 mb-1">
    <span
      class="w-2 h-2 rounded-full flex-shrink-0"
      style="background-color: {app.profile_color ?? '#6366f1'}"
    ></span>
    <span class="text-sm font-semibold truncate">{app.company_name}</span>
  </div>

  <p class="text-xs text-muted-foreground mb-2 pl-4 truncate">{app.role_title || '—'}</p>

  <div class="flex items-center justify-between pl-4">
    <span class="text-[10px] text-muted-foreground">{formatDate(app.applied_date) ?? ''}</span>
    <div class="flex items-center gap-1">
      {#if app.match_score !== null}
        <span class="text-[10px] font-medium px-1.5 py-0.5 rounded {matchColor}">
          {app.match_score}%
        </span>
      {/if}
      {#if app.linked_cover_letter_id}
        <span class="text-[10px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">CL</span>
      {/if}
      {#if app.linked_cv_id}
        <span class="text-[10px] bg-purple-500/10 text-purple-400 px-1.5 py-0.5 rounded">CV</span>
      {/if}
    </div>
  </div>

  {#if !app.linked_cover_letter_id && !app.linked_cv_id}
    <p class="text-[10px] text-muted-foreground/50 pl-4 mt-1 italic">no docs linked</p>
  {/if}
</button>
```

- [ ] **Step 2: Commit**

```bash
rtk git add frontend/src/lib/components/tracker/
rtk git commit -m "feat: add ApplicationCard component"
```

---

### Task 7: Detail Panel Component

**Files:**
- Create: `frontend/src/lib/components/tracker/DetailPanel.svelte`

- [ ] **Step 1: Create the detail panel**

```svelte
<script lang="ts">
  import {
    deleteApplication,
    getApplication,
    updateApplication,
  } from '$lib/api';
  import { toastState } from '$lib/toast.svelte';
  import type { ApplicationEntry, ApplicationStatus, UpdateApplicationRequest } from '$lib/types';

  let {
    app,
    onclose,
    onupdate,
    ondelete,
  }: {
    app: ApplicationEntry;
    onclose: () => void;
    onupdate: (updated: ApplicationEntry) => void;
    ondelete: (id: number) => void;
  } = $props();

  const STATUS_OPTIONS: ApplicationStatus[] = ['applied', 'interviewing', 'offer', 'rejected'];
  let confirmDelete = $state(false);
  let saving = $state(false);

  async function patch(data: UpdateApplicationRequest) {
    try {
      saving = true;
      const updated = await updateApplication(app.id, data);
      onupdate(updated);
    } catch (e: any) {
      toastState.error(e.message);
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    try {
      await deleteApplication(app.id);
      ondelete(app.id);
    } catch (e: any) {
      toastState.error(e.message);
    }
  }
</script>

<div
  class="fixed inset-y-0 right-0 w-96 bg-card border-l border-border shadow-xl z-50 flex flex-col animate-in slide-in-from-right duration-300"
>
  <!-- Header -->
  <div class="flex items-start justify-between p-4 border-b border-border">
    <div class="flex-1 min-w-0 pr-3">
      <h2 class="font-semibold truncate">{app.company_name}</h2>
      <p class="text-sm text-muted-foreground truncate">{app.role_title || '—'}</p>
    </div>
    <button onclick={onclose} class="text-muted-foreground hover:text-foreground p-1 rounded">✕</button>
  </div>

  <!-- Body -->
  <div class="flex-1 overflow-y-auto p-4 space-y-4">
    <!-- Status -->
    <div>
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Status</label>
      <select
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        value={app.status}
        onchange={(e) => patch({ status: (e.target as HTMLSelectElement).value as ApplicationStatus })}
      >
        {#each STATUS_OPTIONS as s}
          <option value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
        {/each}
      </select>
    </div>

    <!-- Company -->
    <div>
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Company</label>
      <input
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        value={app.company_name}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value.trim();
          if (v && v !== app.company_name) patch({ company_name: v });
        }}
      />
    </div>

    <!-- Role -->
    <div>
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Role</label>
      <input
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        value={app.role_title}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value;
          if (v !== app.role_title) patch({ role_title: v });
        }}
      />
    </div>

    <!-- Applied date -->
    <div>
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Applied date</label>
      <input
        type="date"
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        value={app.applied_date ?? ''}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value || null;
          if (v !== app.applied_date) patch({ applied_date: v });
        }}
      />
    </div>

    <!-- Job URL -->
    <div>
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Job URL</label>
      <input
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        placeholder="https://..."
        value={app.job_url ?? ''}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value || null;
          if (v !== app.job_url) patch({ job_url: v });
        }}
      />
    </div>

    <!-- Notes -->
    <div>
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Notes</label>
      <textarea
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm min-h-[80px] resize-none"
        placeholder="Add notes..."
        onblur={(e) => {
          const v = (e.target as HTMLTextAreaElement).value || null;
          if (v !== app.notes) patch({ notes: v });
        }}
      >{app.notes ?? ''}</textarea>
    </div>

    <!-- Linked Documents -->
    {#if app.linked_cover_letter_id || app.linked_cv_id}
      <div>
        <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Linked Documents</p>
        {#if app.linked_cover_letter_id}
          <a
            href="/history?cl={app.linked_cover_letter_id}"
            class="flex items-center gap-2 text-sm text-primary hover:underline mb-1"
          >
            📄 Cover Letter
          </a>
        {/if}
        {#if app.linked_cv_id}
          <a
            href="/history?cv={app.linked_cv_id}"
            class="flex items-center gap-2 text-sm text-primary hover:underline"
          >
            📋 CV
          </a>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Footer -->
  <div class="p-4 border-t border-border">
    {#if confirmDelete}
      <p class="text-sm text-muted-foreground mb-2">Delete this application?</p>
      <div class="flex gap-2">
        <button
          onclick={handleDelete}
          class="flex-1 bg-destructive text-destructive-foreground text-sm py-2 rounded-md hover:bg-destructive/90"
        >Confirm delete</button>
        <button
          onclick={() => (confirmDelete = false)}
          class="flex-1 border border-border text-sm py-2 rounded-md hover:bg-accent"
        >Cancel</button>
      </div>
    {:else}
      <button
        onclick={() => (confirmDelete = true)}
        class="w-full text-destructive border border-destructive/30 text-sm py-2 rounded-md hover:bg-destructive/10"
      >Delete Application</button>
    {/if}
  </div>
</div>

<!-- Backdrop -->
<button
  type="button"
  class="fixed inset-0 z-40 bg-black/20"
  onclick={onclose}
  aria-label="Close panel"
></button>
```

- [ ] **Step 2: Commit**

```bash
rtk git add frontend/src/lib/components/tracker/
rtk git commit -m "feat: add DetailPanel component"
```

---

### Task 8: Tracker Page

**Files:**
- Create: `frontend/src/routes/tracker/+page.svelte`

- [ ] **Step 1: Create the Kanban page**

```svelte
<script lang="ts">
  import {
    createApplication,
    deleteApplication,
    listApplications,
    updateApplication,
    type ApplicationFilters,
  } from '$lib/api';
  import ApplicationCard from '$lib/components/tracker/ApplicationCard.svelte';
  import DetailPanel from '$lib/components/tracker/DetailPanel.svelte';
  import { toastState } from '$lib/toast.svelte';
  import type { ApplicationEntry, ApplicationStatus, CreateApplicationRequest } from '$lib/types';
  import { dndzone } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';

  // --- State ---
  let apps = $state<ApplicationEntry[]>([]);
  let loading = $state(true);
  let selectedApp = $state<ApplicationEntry | null>(null);

  // Filters
  let search = $state('');
  let dateRange = $state<'all' | 'week' | 'month' | '3months'>('all');
  let matchFilter = $state<'all' | 'high' | 'medium' | 'low'>('all');
  let searchTimer: ReturnType<typeof setTimeout>;

  // Add form state (one per column)
  let addingInColumn = $state<ApplicationStatus | null>(null);
  let newCompany = $state('');
  let newRole = $state('');
  let newDate = $state(new Date().toISOString().split('T')[0]);

  const COLUMNS: { status: ApplicationStatus; label: string; color: string }[] = [
    { status: 'applied', label: 'Applied', color: 'text-muted-foreground' },
    { status: 'interviewing', label: 'Interviewing', color: 'text-amber-500' },
    { status: 'offer', label: 'Offer', color: 'text-green-500' },
    { status: 'rejected', label: 'Rejected', color: 'text-red-500' },
  ];

  // --- Derived ---
  const colItems = $derived(
    Object.fromEntries(
      COLUMNS.map((c) => [c.status, apps.filter((a) => a.status === c.status)])
    ) as Record<ApplicationStatus, ApplicationEntry[]>
  );

  // --- Data loading ---
  async function load() {
    loading = true;
    try {
      const filters: ApplicationFilters = { sort: 'date_desc' };
      if (search) filters.search = search;
      if (matchFilter === 'high') { filters.match_min = 70; }
      else if (matchFilter === 'medium') { filters.match_min = 40; filters.match_max = 69; }
      else if (matchFilter === 'low') { filters.match_max = 39; }

      const today = new Date();
      if (dateRange === 'week') {
        const d = new Date(today); d.setDate(d.getDate() - 7);
        filters.date_from = d.toISOString().split('T')[0];
      } else if (dateRange === 'month') {
        filters.date_from = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;
      } else if (dateRange === '3months') {
        const d = new Date(today); d.setMonth(d.getMonth() - 3);
        filters.date_from = d.toISOString().split('T')[0];
      }

      const res = await listApplications(filters);
      apps = res.items;
    } catch (e: any) {
      toastState.error(e.message);
    } finally {
      loading = false;
    }
  }

  $effect(() => { load(); });

  function onSearchInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(load, 300);
  }

  // --- Drag and drop ---
  function handleDndConsider(status: ApplicationStatus, e: CustomEvent) {
    // Update local state optimistically during drag
    const updated = apps.filter((a) => a.status !== status);
    apps = [...updated, ...e.detail.items.map((i: ApplicationEntry) => ({ ...i, status }))];
  }

  async function handleDndFinalize(status: ApplicationStatus, e: CustomEvent) {
    const draggedApp: ApplicationEntry = e.detail.items.find(
      (i: ApplicationEntry) => i.id === e.detail.info.id
    ) ?? e.detail.items[0];
    if (!draggedApp) return;

    const updated = apps.filter((a) => a.status !== status);
    const newItems = e.detail.items.map((i: ApplicationEntry) => ({ ...i, status }));
    apps = [...updated, ...newItems];

    try {
      await updateApplication(draggedApp.id, { status });
    } catch (err: any) {
      toastState.error(err.message);
      await load(); // revert on error
    }
  }

  // --- Add application ---
  function startAdding(status: ApplicationStatus) {
    addingInColumn = status;
    newCompany = '';
    newRole = '';
    newDate = new Date().toISOString().split('T')[0];
  }

  async function submitAdd() {
    if (!newCompany.trim() || !addingInColumn) return;
    try {
      const req: CreateApplicationRequest = {
        company_name: newCompany.trim(),
        role_title: newRole.trim(),
        status: addingInColumn,
        applied_date: newDate || null,
      };
      const created = await createApplication(req);
      apps = [created, ...apps];
      addingInColumn = null;
    } catch (e: any) {
      toastState.error(e.message);
    }
  }

  // --- Detail panel ---
  function handleUpdate(updated: ApplicationEntry) {
    apps = apps.map((a) => (a.id === updated.id ? updated : a));
    selectedApp = updated;
  }

  function handleDelete(id: number) {
    apps = apps.filter((a) => a.id !== id);
    selectedApp = null;
  }
</script>

<div class="space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold">Application Tracker</h1>
  </div>

  <!-- Filter bar -->
  <div class="flex items-center gap-3 flex-wrap">
    <input
      class="flex-1 min-w-[200px] bg-card border border-border rounded-md px-3 py-2 text-sm"
      placeholder="🔍 Search company or role..."
      bind:value={search}
      oninput={onSearchInput}
    />
    <select
      class="bg-card border border-border rounded-md px-3 py-2 text-sm"
      bind:value={dateRange}
      onchange={load}
    >
      <option value="all">All time</option>
      <option value="week">This week</option>
      <option value="month">This month</option>
      <option value="3months">Last 3 months</option>
    </select>
    <select
      class="bg-card border border-border rounded-md px-3 py-2 text-sm"
      bind:value={matchFilter}
      onchange={load}
    >
      <option value="all">All matches</option>
      <option value="high">High (≥70%)</option>
      <option value="medium">Medium (40–69%)</option>
      <option value="low">Low (&lt;40%)</option>
    </select>
  </div>

  {#if loading}
    <div class="grid grid-cols-4 gap-4">
      {#each COLUMNS as _}
        <div class="bg-card border border-border rounded-xl p-3 h-64 animate-pulse"></div>
      {/each}
    </div>
  {:else}
    <!-- Kanban board -->
    <div class="grid grid-cols-4 gap-4 items-start">
      {#each COLUMNS as col}
        {@const items = colItems[col.status] ?? []}
        <div class="bg-card border border-border rounded-xl p-3 flex flex-col">
          <!-- Column header -->
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-semibold uppercase tracking-wide {col.color}">{col.label}</span>
            <span class="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5">{items.length}</span>
          </div>

          <!-- Cards (dnd zone) -->
          <div
            class="flex flex-col gap-2 min-h-[120px] max-h-[60vh] overflow-y-auto"
            use:dndzone={{ items, flipDurationMs: 150, type: 'applications' }}
            onconsider={(e) => handleDndConsider(col.status, e)}
            onfinalize={(e) => handleDndFinalize(col.status, e)}
          >
            {#each items as app (app.id)}
              <div animate:flip={{ duration: 150 }}>
                <ApplicationCard {app} onclick={() => (selectedApp = app)} />
              </div>
            {/each}
          </div>

          <!-- Add form or button -->
          {#if addingInColumn === col.status}
            <form
              class="mt-3 space-y-2 border-t border-border pt-3"
              onsubmit={(e) => { e.preventDefault(); submitAdd(); }}
            >
              <input
                class="w-full bg-background border border-border rounded px-2 py-1.5 text-sm"
                placeholder="Company name *"
                bind:value={newCompany}
                required
                autofocus
              />
              <input
                class="w-full bg-background border border-border rounded px-2 py-1.5 text-sm"
                placeholder="Role title"
                bind:value={newRole}
              />
              <input
                type="date"
                class="w-full bg-background border border-border rounded px-2 py-1.5 text-sm"
                bind:value={newDate}
              />
              <div class="flex gap-2">
                <button
                  type="button"
                  onclick={() => (addingInColumn = null)}
                  class="flex-1 border border-border text-xs py-1.5 rounded hover:bg-accent"
                >Cancel</button>
                <button
                  type="submit"
                  class="flex-1 bg-primary text-primary-foreground text-xs py-1.5 rounded hover:bg-primary/90"
                >Add →</button>
              </div>
            </form>
          {:else}
            <button
              type="button"
              onclick={() => startAdding(col.status)}
              class="mt-3 w-full border border-dashed border-border rounded-md py-2 text-xs text-muted-foreground hover:text-foreground hover:border-muted-foreground transition-colors"
            >+ Add application</button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Detail panel -->
{#if selectedApp}
  <DetailPanel
    app={selectedApp}
    onclose={() => (selectedApp = null)}
    onupdate={handleUpdate}
    ondelete={handleDelete}
  />
{/if}
```

- [ ] **Step 2: Verify the page loads**

Start the dev server:
```bash
cd frontend && bun dev
```

Navigate to `http://localhost:5173/tracker`. Expected: Kanban board renders with 4 columns and filter bar.

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/routes/tracker/
rtk git commit -m "feat: add Tracker Kanban page"
```

---

### Task 9: Add Tracker to Nav

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: Add Tracker link to navLinks array**

In `+layout.svelte`, add to the `navLinks` array after History:

```typescript
const navLinks = [
  { href: '/', label: 'Dashboard' },
  { href: '/profile', label: 'Profile' },
  { href: '/generate', label: 'Generate CV' },
  { href: '/cover-letter', label: 'Cover Letter' },
  { href: '/profiles', label: 'Profiles' },
  { href: '/history', label: 'History' },
  { href: '/tracker', label: 'Tracker' },
];
```

- [ ] **Step 2: Commit**

```bash
rtk git add frontend/src/routes/+layout.svelte
rtk git commit -m "feat: add Tracker link to nav"
```

---

### Task 10: Tracker Checkbox on Cover Letter Page

**Files:**
- Modify: `frontend/src/routes/cover-letter/+page.svelte`
- Modify: `backend/app/routes/generate.py` (add `application_id` to cover letter save)
- Modify: `backend/app/schemas.py` (extend `CoverLetterRequest`)

- [ ] **Step 1: Extend `CoverLetterRequest` schema**

In `backend/app/schemas.py`, update `CoverLetterRequest`:

```python
class CoverLetterRequest(BaseModel):
    profile_id: int
    job_description: str
    company_name: str | None = None
    extra_context: str = ""
    # Tracker fields
    add_to_tracker: bool = False
    tracker_role_title: str | None = None
    application_id: int | None = None
```

Also extend `CoverLetterResponse` to return the created/linked application id:

```python
class CoverLetterResponse(BaseModel):
    cover_letter_text: str
    application_id: int | None = None
```

- [ ] **Step 2: Update `generate.py` to handle tracker fields**

Open `backend/app/routes/generate.py`. In the cover letter endpoint, after saving the `GeneratedCoverLetter` to the DB, add tracker logic:

```python
from datetime import date

# After db.add(letter) and db.commit():
app_id: int | None = body.application_id

if body.add_to_tracker and not app_id:
    from app.models import Application
    tracker_app = Application(
        company_name=body.company_name or "",
        role_title=body.tracker_role_title or "",
        status="applied",
        job_url=getattr(body, "job_url", None),
        applied_date=date.today(),
        profile_id=body.profile_id,
    )
    db.add(tracker_app)
    db.commit()
    db.refresh(tracker_app)
    app_id = tracker_app.id

if app_id:
    letter.application_id = app_id
    db.commit()
```

Return `application_id` in the response:
```python
return CoverLetterResponse(cover_letter_text=letter_text, application_id=app_id)
```

- [ ] **Step 3: Add tracker checkbox to cover letter page**

In `frontend/src/routes/cover-letter/+page.svelte`, add state and UI before the Generate button:

```svelte
<script lang="ts">
  // Add to existing script:
  let trackApp = $state(false);
  let trackerRole = $state('');
  let trackerDate = $state(new Date().toISOString().split('T')[0]);
</script>

<!-- Add between tone selector and Generate button: -->
<div class="border border-border rounded-lg p-3 space-y-2">
  <label class="flex items-center gap-2 cursor-pointer">
    <input type="checkbox" bind:checked={trackApp} class="rounded" />
    <span class="text-sm font-medium">Track this application</span>
  </label>
  {#if trackApp}
    <div class="grid grid-cols-2 gap-2 pt-1 animate-in fade-in duration-200">
      <input
        class="bg-background border border-border rounded px-3 py-2 text-sm"
        placeholder="Role title (optional)"
        bind:value={trackerRole}
      />
      <input
        type="date"
        class="bg-background border border-border rounded px-3 py-2 text-sm"
        bind:value={trackerDate}
      />
    </div>
  {/if}
</div>
```

Pass tracker fields in the generate request:
```typescript
// In the generate function, add to request body:
add_to_tracker: trackApp,
tracker_role_title: trackerRole || null,
// applied_date sent so backend uses the user-picked date, not server today
```

Also extend `CreateApplicationRequest` in `backend/app/schemas.py` to accept `applied_date` as a string from the frontend (`date` type in Pydantic will parse ISO strings automatically):
```python
# applied_date: date | None = None  ← already present, no change needed
```

And in `generate.py` tracker creation block, use the date from the request if provided:
```python
from datetime import date as date_type
tracker_app = Application(
    ...
    applied_date=date_type.fromisoformat(body.tracker_applied_date) if getattr(body, 'tracker_applied_date', None) else date.today(),
)
```

Add `tracker_applied_date: str | None = None` to `CoverLetterRequest` schema.

- [ ] **Step 4: Update `CoverLetterRequest` type in `types.ts`**

```typescript
export interface CoverLetterRequest {
  profile_id: number;
  job_description: string;
  company_name?: string | null;
  extra_context?: string;
  add_to_tracker?: boolean;
  tracker_role_title?: string | null;
  application_id?: number | null;
}

export interface CoverLetterResponse {
  cover_letter_text: string;
  application_id?: number | null;
}
```

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/schemas.py backend/app/routes/generate.py frontend/src/routes/cover-letter/+page.svelte frontend/src/lib/types.ts
rtk git commit -m "feat: add tracker checkbox to cover letter page"
```

---

### Task 11: Push

- [ ] **Step 1: Push all commits**

```bash
rtk git push
```
