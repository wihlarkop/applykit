# Version History Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store every generated CV and cover letter as a history entry so users can browse, re-open, re-download, and delete past generations.

**Architecture:** Two new SQLite tables (`generated_cv`, `generated_cover_letter`) store a frozen snapshot of each generation. Generate routes auto-save to history after each successful generation. A new `/api/history/*` router handles CRUD. The frontend gets a `/history` page (tabs: CV | Cover Letter) and the cover letter page gains a `company_name` field for tracking.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, SvelteKit 2 / Svelte 5, TypeScript, Tailwind CSS v4, shadcn-svelte. Package managers: `uv` (Python), `bun` (JS). No unit tests.

---

## File Map

### Backend — new / modified

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/models.py` | Modify | Add `GeneratedCV` and `GeneratedCoverLetter` models |
| `backend/app/schemas.py` | Modify | Add history schemas; add `company_name` to `CoverLetterRequest` |
| `backend/app/routes/history.py` | **Create** | List / get / delete endpoints for both history types |
| `backend/app/routes/generate.py` | Modify | Auto-save to history after each successful generation |
| `backend/main.py` | Modify | Register history router |
| `backend/migrations/versions/<hash>-add_history_tables.py` | **Create** | Alembic migration for the two new tables |

### Frontend — new / modified

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/lib/types.ts` | Modify | Add `GeneratedCVEntry`, `GeneratedCoverLetterEntry`, list response types; add `company_name` to `CoverLetterRequest` |
| `frontend/src/lib/api.ts` | Modify | Add history API functions; add `company_name` to `generateCoverLetter` |
| `frontend/src/routes/cover-letter/+page.svelte` | Modify | Add company name input field |
| `frontend/src/routes/history/+page.svelte` | **Create** | Tabbed history page (CV tab + Cover Letter tab) |
| `frontend/src/routes/+layout.svelte` | Modify | Add History nav link |

---

## Chunk 1: Backend

### Task 1: Add DB models

**Files:**
- Modify: `backend/app/models.py`

- [ ] Open `backend/app/models.py` and append the two new models below the existing `Profile` class:

```python
class GeneratedCV(Base):
    __tablename__ = "generated_cv"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    enhanced = Column(Integer, default=0)          # 0 = false, 1 = true (SQLite bool)
    profile_snapshot = Column(Text, nullable=False) # JSON string of ProfileData
```

```python
class GeneratedCoverLetter(Base):
    __tablename__ = "generated_cover_letter"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    company_name = Column(String, nullable=True)
    job_description = Column(Text, nullable=False)
    extra_context = Column(Text, nullable=True)
    cover_letter_text = Column(Text, nullable=False)
```

- [ ] Confirm the file top already imports `UTC, datetime, Column, DateTime, Integer, String, Text` — no new imports needed.

- [ ] Commit:
```bash
cd backend
rtk git add app/models.py
rtk git commit -m "feat: add GeneratedCV and GeneratedCoverLetter models"
```

---

### Task 2: Alembic migration

**Files:**
- Create: `backend/migrations/versions/<hash>-add_history_tables.py` (auto-generated)

- [ ] Generate the migration:
```bash
cd backend
uv run alembic revision --autogenerate -m "add history tables"
```
Expected: a new file created under `migrations/versions/`.

- [ ] Open the generated file and verify `upgrade()` contains `create_table` calls for both `generated_cv` and `generated_cover_letter`. It should look like:

```python
def upgrade() -> None:
    op.create_table(
        "generated_cv",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("enhanced", sa.Integer(), nullable=True),
        sa.Column("profile_snapshot", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "generated_cover_letter",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("company_name", sa.String(), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("extra_context", sa.Text(), nullable=True),
        sa.Column("cover_letter_text", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

def downgrade() -> None:
    op.drop_table("generated_cover_letter")
    op.drop_table("generated_cv")
```

- [ ] Apply the migration:
```bash
uv run alembic upgrade head
```
Expected output: `Running upgrade <prev_hash> -> <new_hash>, add history tables`

- [ ] Commit:
```bash
rtk git add migrations/
rtk git commit -m "feat: migration for history tables"
```

---

### Task 3: History schemas + update CoverLetterRequest

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] Add `company_name` to `CoverLetterRequest`:

```python
class CoverLetterRequest(BaseModel):
    job_description: str
    company_name: str | None = None   # ← add this line
    extra_context: str = ""
```

- [ ] Append history schemas at the bottom of `schemas.py`:

```python
# --- History schemas ---

class GeneratedCVEntry(BaseModel):
    id: int
    created_at: datetime
    enhanced: bool
    profile_snapshot: str  # raw JSON — frontend parses if needed

    model_config = {"from_attributes": True}


class GeneratedCVListResponse(BaseModel):
    items: list[GeneratedCVEntry]


class GeneratedCoverLetterEntry(BaseModel):
    id: int
    created_at: datetime
    company_name: str | None
    job_description: str
    extra_context: str | None
    cover_letter_text: str

    model_config = {"from_attributes": True}


class GeneratedCoverLetterListResponse(BaseModel):
    items: list[GeneratedCoverLetterEntry]
```

- [ ] Commit:
```bash
rtk git add app/schemas.py
rtk git commit -m "feat: history schemas, add company_name to CoverLetterRequest"
```

---

### Task 4: History routes

**Files:**
- Create: `backend/app/routes/history.py`

- [ ] Create `backend/app/routes/history.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GeneratedCV, GeneratedCoverLetter
from app.schemas import (
    GeneratedCoverLetterEntry,
    GeneratedCoverLetterListResponse,
    GeneratedCVEntry,
    GeneratedCVListResponse,
)

router = APIRouter()


# --- CV history ---

@router.get("/history/cv", response_model=GeneratedCVListResponse)
def list_cv_history(db: Session = Depends(get_db)):
    items = (
        db.query(GeneratedCV)
        .order_by(GeneratedCV.created_at.desc())
        .all()
    )
    return GeneratedCVListResponse(items=items)


@router.get("/history/cv/{entry_id}", response_model=GeneratedCVEntry)
def get_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return entry


@router.delete("/history/cv/{entry_id}", status_code=204)
def delete_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    db.delete(entry)
    db.commit()


# --- Cover letter history ---

@router.get("/history/cover-letter", response_model=GeneratedCoverLetterListResponse)
def list_cover_letter_history(db: Session = Depends(get_db)):
    items = (
        db.query(GeneratedCoverLetter)
        .order_by(GeneratedCoverLetter.created_at.desc())
        .all()
    )
    return GeneratedCoverLetterListResponse(items=items)


@router.get("/history/cover-letter/{entry_id}", response_model=GeneratedCoverLetterEntry)
def get_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return entry


@router.delete("/history/cover-letter/{entry_id}", status_code=204)
def delete_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    db.delete(entry)
    db.commit()
```

- [ ] Commit:
```bash
rtk git add app/routes/history.py
rtk git commit -m "feat: history list/get/delete routes for CV and cover letter"
```

---

### Task 5: Auto-save in generate routes + register history router

**Files:**
- Modify: `backend/app/routes/generate.py`
- Modify: `backend/main.py`

- [ ] In `backend/app/routes/generate.py`, add imports at the top:

```python
from app.models import GeneratedCV, GeneratedCoverLetter
```

- [ ] In `generate_cv()`, after `return GenerateCvResponse(...)` is built but before returning, save to history. Replace the final `return` with:

```python
    # Save to history
    entry = GeneratedCV(
        enhanced=enhanced,
        profile_snapshot=result_profile.model_dump_json(),
    )
    db.add(entry)
    db.commit()

    return GenerateCvResponse(enhanced=enhanced, profile=result_profile)
```

- [ ] In `generate_cover_letter()`, the request body already has `company_name` (from schema update in Task 3). After `text = call_llm(...)`, save to history before returning:

```python
    # Save to history
    entry = GeneratedCoverLetter(
        company_name=req.company_name,
        job_description=req.job_description,
        extra_context=req.extra_context or None,
        cover_letter_text=text,
    )
    db.add(entry)
    db.commit()

    return CoverLetterResponse(cover_letter_text=text)
```

- [ ] In `backend/main.py`, import and register the history router. Add to imports:

```python
from app.routes import generate, history, import_cv, profile
```

And register it (alongside the others):

```python
app.include_router(history.router, prefix="/api")
```

- [ ] Verify all routes are registered:
```bash
cd backend
uv run python -c "from main import app; [print(r.path) for r in app.routes]"
```
Expected new routes: `/api/history/cv`, `/api/history/cv/{entry_id}`, `/api/history/cover-letter`, `/api/history/cover-letter/{entry_id}`

- [ ] Commit:
```bash
rtk git add app/routes/generate.py main.py
rtk git commit -m "feat: auto-save CV and cover letter generations to history"
```

---

## Chunk 2: Frontend

### Task 6: Types + API client

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] In `frontend/src/lib/types.ts`, add `company_name` to `CoverLetterRequest` and append history types:

```typescript
// Update existing
export interface CoverLetterRequest {
  job_description: string;
  company_name?: string | null;   // ← add this
  extra_context?: string;
}

// Append at bottom
export interface GeneratedCVEntry {
  id: number;
  created_at: string;
  enhanced: boolean;
  profile_snapshot: string; // JSON string — parse with JSON.parse() when needed
}

export interface GeneratedCVListResponse {
  items: GeneratedCVEntry[];
}

export interface GeneratedCoverLetterEntry {
  id: number;
  created_at: string;
  company_name: string | null;
  job_description: string;
  extra_context: string | null;
  cover_letter_text: string;
}

export interface GeneratedCoverLetterListResponse {
  items: GeneratedCoverLetterEntry[];
}
```

- [ ] In `frontend/src/lib/api.ts`, add history functions at the bottom:

```typescript
import type {
  // ... existing imports ...
  GeneratedCVListResponse,
  GeneratedCVEntry,
  GeneratedCoverLetterListResponse,
  GeneratedCoverLetterEntry,
} from './types';

// CV history
export const getCvHistory = () =>
  request<GeneratedCVListResponse>('/history/cv');

export const getCvHistoryEntry = (id: number) =>
  request<GeneratedCVEntry>(`/history/cv/${id}`);

export const deleteCvHistoryEntry = (id: number) =>
  request<void>(`/history/cv/${id}`, { method: 'DELETE' });

// Cover letter history
export const getCoverLetterHistory = () =>
  request<GeneratedCoverLetterListResponse>('/history/cover-letter');

export const getCoverLetterHistoryEntry = (id: number) =>
  request<GeneratedCoverLetterEntry>(`/history/cover-letter/${id}`);

export const deleteCoverLetterHistoryEntry = (id: number) =>
  request<void>(`/history/cover-letter/${id}`, { method: 'DELETE' });
```

- [ ] Run type-check to confirm no errors:
```bash
cd frontend
bun run check
```
Expected: 0 errors, 0 warnings.

- [ ] Commit:
```bash
rtk git add src/lib/types.ts src/lib/api.ts
rtk git commit -m "feat: history types and API client functions"
```

---

### Task 7: Update cover letter page — add company name field

**Files:**
- Modify: `frontend/src/routes/cover-letter/+page.svelte`

- [ ] Read the current file first, then:
  - Add a `companyName` state variable: `let companyName = $state('');`
  - Add a company name `Input` field above the job description textarea:

```svelte
<div class="space-y-3">
  <Label for="company">Company Name (optional)</Label>
  <Input
    id="company"
    bind:value={companyName}
    placeholder="e.g. Acme Corp"
  />
</div>
```

  - Pass `company_name` to `generateCoverLetter`:

```typescript
const res = await generateCoverLetter({
  job_description: jobDescription,
  company_name: companyName.trim() || null,
  extra_context: extraContext,
});
```

- [ ] Commit:
```bash
rtk git add src/routes/cover-letter/+page.svelte
rtk git commit -m "feat: add company name field to cover letter page"
```

---

### Task 8: History page

**Files:**
- Create: `frontend/src/routes/history/+page.svelte`

- [ ] Create `frontend/src/routes/history/+page.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getCvHistory,
    getCoverLetterHistory,
    deleteCvHistoryEntry,
    deleteCoverLetterHistoryEntry,
  } from '$lib/api';
  import type { GeneratedCVEntry, GeneratedCoverLetterEntry } from '$lib/types';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import CvPreview from '$lib/components/CvPreview.svelte';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';
  import type { ProfileData } from '$lib/types';

  type Tab = 'cv' | 'cover-letter';
  let tab: Tab = $state('cv');

  let cvItems: GeneratedCVEntry[] = $state([]);
  let clItems: GeneratedCoverLetterEntry[] = $state([]);
  let loading = $state(true);
  let errorMsg = $state('');

  // selected entry for preview panel
  let selectedCv: GeneratedCVEntry | null = $state(null);
  let selectedCl: GeneratedCoverLetterEntry | null = $state(null);

  onMount(async () => {
    try {
      const [cvRes, clRes] = await Promise.all([getCvHistory(), getCoverLetterHistory()]);
      cvItems = cvRes.items;
      clItems = clRes.items;
    } catch (e: any) {
      errorMsg = e.message;
    } finally {
      loading = false;
    }
  });

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  }

  async function handleDeleteCv(id: number) {
    await deleteCvHistoryEntry(id);
    cvItems = cvItems.filter((e) => e.id !== id);
    if (selectedCv?.id === id) selectedCv = null;
  }

  async function handleDeleteCl(id: number) {
    await deleteCoverLetterHistoryEntry(id);
    clItems = clItems.filter((e) => e.id !== id);
    if (selectedCl?.id === id) selectedCl = null;
  }

  function parseCvProfile(entry: GeneratedCVEntry): ProfileData {
    return JSON.parse(entry.profile_snapshot) as ProfileData;
  }

  function handlePrint() {
    window.print();
  }
</script>

<div class="space-y-6">
  <h1 class="text-2xl font-bold">History</h1>

  <!-- Tabs -->
  <div class="flex gap-2 border-b">
    <button
      class="px-4 py-2 text-sm font-medium transition-colors
        {tab === 'cv' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
      onclick={() => { tab = 'cv'; selectedCv = null; }}
    >
      Generated CVs ({cvItems.length})
    </button>
    <button
      class="px-4 py-2 text-sm font-medium transition-colors
        {tab === 'cover-letter' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
      onclick={() => { tab = 'cover-letter'; selectedCl = null; }}
    >
      Cover Letters ({clItems.length})
    </button>
  </div>

  {#if loading}
    <p class="text-muted-foreground">Loading…</p>
  {:else if errorMsg}
    <p class="text-sm text-destructive">{errorMsg}</p>
  {:else}

    <!-- CV tab -->
    {#if tab === 'cv'}
      {#if cvItems.length === 0}
        <p class="text-muted-foreground">No CVs generated yet. <a href="/generate" class="underline">Generate one</a>.</p>
      {:else}
        <div class="grid gap-4 lg:grid-cols-[280px_1fr]">
          <!-- List -->
          <div class="space-y-2">
            {#each cvItems as entry}
              <button
                onclick={() => selectedCv = entry}
                class="w-full text-left border rounded-lg p-3 transition-colors hover:bg-accent
                  {selectedCv?.id === entry.id ? 'border-primary bg-accent' : 'bg-card'}"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="text-sm font-medium truncate">{formatDate(entry.created_at)}</span>
                  {#if entry.enhanced}
                    <Badge variant="default" class="text-xs shrink-0">AI</Badge>
                  {:else}
                    <Badge variant="secondary" class="text-xs shrink-0">Raw</Badge>
                  {/if}
                </div>
              </button>
            {/each}
          </div>

          <!-- Preview panel -->
          {#if selectedCv}
            <div class="border rounded-lg overflow-hidden bg-white">
              <div class="flex items-center justify-between gap-2 p-3 border-b bg-muted/30">
                <span class="text-sm text-muted-foreground">{formatDate(selectedCv.created_at)}</span>
                <div class="flex gap-2">
                  <Button variant="outline" size="sm" onclick={handlePrint}>Print</Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onclick={() => selectedCv && handleDeleteCv(selectedCv.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
              <div class="overflow-auto max-h-[70vh]">
                <CvPreview profile={parseCvProfile(selectedCv)} />
              </div>
            </div>
          {:else}
            <div class="border rounded-lg p-8 text-center text-muted-foreground">
              Select an entry to preview.
            </div>
          {/if}
        </div>
      {/if}
    {/if}

    <!-- Cover letter tab -->
    {#if tab === 'cover-letter'}
      {#if clItems.length === 0}
        <p class="text-muted-foreground">No cover letters generated yet. <a href="/cover-letter" class="underline">Write one</a>.</p>
      {:else}
        <div class="grid gap-4 lg:grid-cols-[280px_1fr]">
          <!-- List -->
          <div class="space-y-2">
            {#each clItems as entry}
              <button
                onclick={() => selectedCl = entry}
                class="w-full text-left border rounded-lg p-3 transition-colors hover:bg-accent
                  {selectedCl?.id === entry.id ? 'border-primary bg-accent' : 'bg-card'}"
              >
                <div class="text-sm font-medium truncate">
                  {entry.company_name ?? 'Unknown Company'}
                </div>
                <div class="text-xs text-muted-foreground mt-0.5">{formatDate(entry.created_at)}</div>
              </button>
            {/each}
          </div>

          <!-- Preview panel -->
          {#if selectedCl}
            <div class="border rounded-lg overflow-hidden bg-white">
              <div class="flex items-center justify-between gap-2 p-3 border-b bg-muted/30">
                <div>
                  <span class="text-sm font-medium">{selectedCl.company_name ?? 'Unknown Company'}</span>
                  <span class="text-xs text-muted-foreground ml-2">{formatDate(selectedCl.created_at)}</span>
                </div>
                <div class="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onclick={() => navigator.clipboard.writeText(selectedCl?.cover_letter_text ?? '')}
                  >
                    Copy
                  </Button>
                  <Button variant="outline" size="sm" onclick={handlePrint}>Print</Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onclick={() => selectedCl && handleDeleteCl(selectedCl.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
              <div class="overflow-auto max-h-[70vh]">
                <CoverLetterPreview text={selectedCl.cover_letter_text} />
              </div>
            </div>
          {:else}
            <div class="border rounded-lg p-8 text-center text-muted-foreground">
              Select an entry to preview.
            </div>
          {/if}
        </div>
      {/if}
    {/if}

  {/if}
</div>

<style>
  @media print {
    :global(header), :global(nav) { display: none !important; }
  }
</style>
```

- [ ] Commit:
```bash
rtk git add src/routes/history/+page.svelte
rtk git commit -m "feat: history page with CV and cover letter tabs"
```

---

### Task 9: Add History to nav

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] In `+layout.svelte`, add `{ href: '/history', label: 'History' }` to the `navLinks` array:

```typescript
const navLinks = [
  { href: '/', label: 'Dashboard' },
  { href: '/profile', label: 'Profile' },
  { href: '/generate', label: 'Generate CV' },
  { href: '/cover-letter', label: 'Cover Letter' },
  { href: '/history', label: 'History' },   // ← add this
];
```

- [ ] Run final type-check:
```bash
cd frontend
bun run check
```
Expected: 0 errors.

- [ ] Run backend smoke test:
```bash
cd backend
uv run python -c "
from main import app
paths = [r.path for r in app.routes]
assert '/api/history/cv' in paths
assert '/api/history/cover-letter' in paths
print('All history routes registered:', [p for p in paths if 'history' in p])
"
```

- [ ] Commit:
```bash
rtk git add src/routes/+layout.svelte
rtk git commit -m "feat: add History link to nav"
```

---

## Summary

After all tasks, the flow is:

1. User generates a CV → backend saves `GeneratedCV` row (profile snapshot + enhanced flag) → user can see it in `/history` CV tab
2. User generates a cover letter (optionally enters company name) → backend saves `GeneratedCoverLetter` row → user can see it in `/history` Cover Letter tab, listed by company name
3. From history, user can preview any past generation, print it, copy it (cover letters), or delete it
