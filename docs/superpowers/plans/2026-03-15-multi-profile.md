# Multi-Profile Support Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to maintain multiple professional identities (e.g. "Software Engineer" vs "Technical Manager"), each with its own profile data, color dot, and emoji icon, with a shared history list tagged per-profile.

**Architecture:** Replace the hardcoded `id=1` Profile pattern with a proper multi-row `profiles` resource. The frontend stores the active profile ID in localStorage via a Svelte 5 rune store. A `ProfileSwitcher` dropdown component lives on the Profile, Generate, and Cover Letter pages. History entries are tagged with `profile_id` and show a color/icon badge.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, SQLite, SvelteKit 2, Svelte 5 runes, Tailwind CSS v4, shadcn-svelte. Package managers: `uv` (Python), `bun` (JS). No unit tests.

**Spec:** `docs/superpowers/specs/2026-03-15-multi-profile-design.md`

---

## File Map

### Backend — modified
| File | Change |
|------|--------|
| `backend/app/models.py` | Add `label`, `color`, `icon` to Profile; remove `default=1`; add `profile_id` FK to history tables |
| `backend/app/schemas.py` | Update `ProfileData`; add `ProfileListItem`, `ProfileListResponse`, `CreateProfileRequest`, `GenerateCvRequest`; update history schemas |
| `backend/app/utils.py` | Update `profile_to_schema` to include `id`, `label`, `color`, `icon` |
| `backend/app/routes/profile.py` | Remove `GET /api/profile` and `POST /api/profile`; update onboarding to check any profile |
| `backend/app/routes/generate.py` | Add `GenerateCvRequest` body to `generate_cv()`; update `_get_profile_or_404` → lookup by `profile_id`; save `profile_id` to history |
| `backend/app/routes/history.py` | Join Profile table to populate `profile_label/color/icon` in list responses |
| `backend/main.py` | Register profiles router |

### Backend — new
| File | Purpose |
|------|---------|
| `backend/app/routes/profiles.py` | CRUD for profiles resource: list, create, get, put, delete |
| `backend/migrations/versions/<hash>_add_multi_profile_support.py` | Alembic migration |

### Frontend — modified
| File | Change |
|------|--------|
| `frontend/src/lib/types.ts` | Add `ProfileListItem`, `ProfileListResponse`, `CreateProfileRequest`, `GenerateCvRequest`; add `id/label/color/icon` to `ProfileData`; add profile fields to history types |
| `frontend/src/lib/api.ts` | Add `listProfiles`, `createProfile`, `getProfile`, `saveProfile`, `deleteProfile`; update `generateCv`, `generateCoverLetter` |
| `frontend/src/routes/+layout.ts` | Replace `getProfile()` with `listProfiles()`; init `profiles` and `activeProfile` stores |
| `frontend/src/routes/+layout.svelte` | Add "Profiles" nav link |
| `frontend/src/routes/profile/+page.svelte` | Add `ProfileSwitcher`; load/save by active `profile_id` |
| `frontend/src/routes/generate/+page.svelte` | Add `ProfileSwitcher`; pass `profile_id` in generate request |
| `frontend/src/routes/cover-letter/+page.svelte` | Add `ProfileSwitcher`; pass `profile_id` in cover letter request |
| `frontend/src/routes/history/+page.svelte` | Show color dot + icon badge on each entry |

### Frontend — new
| File | Purpose |
|------|---------|
| `frontend/src/lib/profiles.svelte.ts` | Svelte 5 `$state` store — full list of `ProfileListItem[]` |
| `frontend/src/lib/activeProfile.svelte.ts` | Svelte 5 `$state` store — active profile, persisted to localStorage |
| `frontend/src/lib/components/ProfileSwitcher.svelte` | Dropdown button; reads `profiles` store; opens `ProfileModal` |
| `frontend/src/lib/components/ProfileModal.svelte` | Create/edit modal with label, color swatches, icon tiles, clone |
| `frontend/src/routes/profiles/+page.svelte` | Profile management page |

---

## Chunk 1: Backend

### Task 1: Update models.py

**Files:**
- Modify: `backend/app/models.py`

- [ ] Read `backend/app/models.py` to confirm current state.

- [ ] In `Profile` class: remove `id = Column(Integer, primary_key=True, default=1)` and replace with:
```python
id = Column(Integer, primary_key=True, autoincrement=True)
```
Then add three new columns after `id`:
```python
label = Column(String, nullable=False, default="Default")
color = Column(String, nullable=False, default="#6366f1")
icon  = Column(String, nullable=False, default="💼")
```

- [ ] In `GeneratedCV` class, add after `profile_snapshot`:
```python
profile_id = Column(Integer, ForeignKey("profile.id"), nullable=True)
```

- [ ] In `GeneratedCoverLetter` class, add after `cover_letter_text`:
```python
profile_id = Column(Integer, ForeignKey("profile.id"), nullable=True)
```

- [ ] Add `ForeignKey` to the SQLAlchemy imports at the top:
```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
```

- [ ] Commit:
```bash
cd backend
rtk git add app/models.py
rtk git commit -m "feat: add label/color/icon to Profile, profile_id FK to history tables"
```

---

### Task 2: Update schemas.py

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] Read `backend/app/schemas.py` to confirm current state.

- [ ] Update `ProfileData` — add four new optional fields at the top of the class (before `name`):
```python
class ProfileData(BaseModel):
    id: int | None = None
    label: str = "Default"
    color: str = "#6366f1"
    icon: str = "💼"
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    summary: str | None = None
    work_experience: list[WorkExperience] = []
    education: list[Education] = []
    skills: list[str] = []
    projects: list[Project] = []
    certifications: list[Certification] = []
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
```

- [ ] Add new schemas after `ProfileResponse`. Insert these before `OnboardingStatusResponse`:
```python
class ProfileListItem(BaseModel):
    id: int
    label: str
    color: str
    icon: str
    name: str

    model_config = {"from_attributes": True}


class ProfileListResponse(BaseModel):
    items: list[ProfileListItem]


class CreateProfileRequest(BaseModel):
    label: str
    color: str
    icon: str
    clone_from_id: int | None = None


class GenerateCvRequest(BaseModel):
    profile_id: int
    enhance: bool = True
```

- [ ] Update `CoverLetterRequest` — add `profile_id` field:
```python
class CoverLetterRequest(BaseModel):
    profile_id: int
    job_description: str
    company_name: str | None = None
    extra_context: str = ""
```

- [ ] Update history schemas — add profile identity fields to both `GeneratedCVEntry` and `GeneratedCoverLetterEntry`:
```python
class GeneratedCVEntry(BaseModel):
    id: int
    created_at: datetime
    enhanced: bool
    profile_snapshot: str
    profile_id: int | None = None
    profile_label: str | None = None
    profile_color: str | None = None
    profile_icon: str | None = None

    model_config = {"from_attributes": True}


class GeneratedCoverLetterEntry(BaseModel):
    id: int
    created_at: datetime
    company_name: str | None
    job_description: str
    extra_context: str | None
    cover_letter_text: str
    profile_id: int | None = None
    profile_label: str | None = None
    profile_color: str | None = None
    profile_icon: str | None = None

    model_config = {"from_attributes": True}
```

- [ ] Commit:
```bash
rtk git add app/schemas.py
rtk git commit -m "feat: update schemas for multi-profile support"
```

---

### Task 3: Update utils.py

**Files:**
- Modify: `backend/app/utils.py`

- [ ] Read `backend/app/utils.py`.

- [ ] Update `profile_to_schema` to include the new identity fields:
```python
def profile_to_schema(p: Profile) -> ProfileData:
    return ProfileData(
        id=p.id,
        label=p.label,
        color=p.color,
        icon=p.icon,
        name=p.name,
        email=p.email,
        phone=p.phone,
        location=p.location,
        linkedin=p.linkedin,
        github=p.github,
        portfolio=p.portfolio,
        summary=p.summary,
        work_experience=json.loads(p.work_experience or "[]"),
        education=json.loads(p.education or "[]"),
        skills=json.loads(p.skills or "[]"),
        projects=json.loads(p.projects or "[]"),
        certifications=json.loads(p.certifications or "[]"),
        updated_at=p.updated_at,
    )
```

- [ ] Commit:
```bash
rtk git add app/utils.py
rtk git commit -m "feat: include id/label/color/icon in profile_to_schema"
```

---

### Task 4: Create profiles router

**Files:**
- Create: `backend/app/routes/profiles.py`

- [ ] Create `backend/app/routes/profiles.py`:
```python
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import (
    CreateProfileRequest,
    ProfileData,
    ProfileListItem,
    ProfileListResponse,
)
from app.utils import profile_to_schema

router = APIRouter()

JSON_FIELDS = {"work_experience", "education", "skills", "projects", "certifications"}


def _get_or_404(db: Session, profile_id: int) -> Profile:
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Profile not found", "code": "NOT_FOUND"},
        )
    return profile


@router.get("/profiles", response_model=ProfileListResponse)
def list_profiles(db: Session = Depends(get_db)):
    items = db.query(Profile).order_by(Profile.id).all()
    return ProfileListResponse(items=items)


@router.post("/profiles", response_model=ProfileData, status_code=201)
def create_profile(req: CreateProfileRequest, db: Session = Depends(get_db)):
    if req.clone_from_id is not None:
        source = _get_or_404(db, req.clone_from_id)
        profile = Profile(
            label=req.label,
            color=req.color,
            icon=req.icon,
            name=source.name,
            email=source.email,
            phone=source.phone,
            location=source.location,
            linkedin=source.linkedin,
            github=source.github,
            portfolio=source.portfolio,
            summary=source.summary,
            work_experience=source.work_experience,
            education=source.education,
            skills=source.skills,
            projects=source.projects,
            certifications=source.certifications,
        )
    else:
        profile = Profile(
            label=req.label,
            color=req.color,
            icon=req.icon,
            name="",
            email="",
        )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile_to_schema(profile)


@router.get("/profiles/{profile_id}", response_model=ProfileData)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    return profile_to_schema(_get_or_404(db, profile_id))


@router.put("/profiles/{profile_id}", response_model=ProfileData)
def save_profile(profile_id: int, data: ProfileData, db: Session = Depends(get_db)):
    profile = _get_or_404(db, profile_id)
    fields = data.model_dump(exclude={"id", "updated_at"})

    for key, value in fields.items():
        if key in JSON_FIELDS:
            setattr(
                profile,
                key,
                json.dumps(
                    [v.model_dump() if hasattr(v, "model_dump") else v for v in value]
                ),
            )
        else:
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile_to_schema(profile)


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = _get_or_404(db, profile_id)
    db.delete(profile)
    db.commit()
```

- [ ] Commit:
```bash
rtk git add app/routes/profiles.py
rtk git commit -m "feat: profiles CRUD router (list, create, get, put, delete)"
```

---

### Task 5: Update profile.py — remove old endpoints, fix onboarding

**Files:**
- Modify: `backend/app/routes/profile.py`

- [ ] Read `backend/app/routes/profile.py`.

- [ ] Remove the `get_profile` and `save_profile` route functions entirely (the `GET /api/profile` and `POST /api/profile` endpoints).

- [ ] Update `get_onboarding_status` to check any profile (not just id=1):
```python
@router.get("/onboarding", response_model=OnboardingStatusResponse)
def get_onboarding_status(db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.name != None, Profile.name != "").first()
    is_onboarded = profile is not None
    return OnboardingStatusResponse(is_onboarded=is_onboarded)
```

- [ ] Remove unused imports: `ProfileData`, `ProfileResponse`, `profile_to_schema` (all callers in this file are being deleted).

  Final imports should be:
```python
import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import OnboardingStatusResponse, StatusResponse

router = APIRouter()
```

- [ ] Commit:
```bash
rtk git add app/routes/profile.py
rtk git commit -m "feat: remove old /api/profile endpoints, fix onboarding for multi-profile"
```

---

### Task 6: Update generate.py — add profile_id to requests

**Files:**
- Modify: `backend/app/routes/generate.py`

- [ ] Read `backend/app/routes/generate.py`.

- [ ] Update imports to add `GenerateCvRequest`:
```python
from app.schemas import (
    ATSEnhancement,
    CoverLetterRequest,
    CoverLetterResponse,
    GenerateCvRequest,
    GenerateCvResponse,
    PdfRequest,
)
```

- [ ] Replace `_get_profile_or_404` with a version that takes `profile_id`:
```python
def _get_profile_or_404(db: Session, profile_id: int) -> Profile:
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": "Profile not found.",
                "code": "PROFILE_NOT_FOUND",
            },
        )
    return profile
```

- [ ] Replace the full `generate_cv` function with this (note: `req.enhance` controls whether the LLM ATS call is attempted; if `False`, the profile is returned as-is without calling the LLM):
```python
@router.post("/generate/cv", response_model=GenerateCvResponse)
def generate_cv(req: GenerateCvRequest, db: Session = Depends(get_db)):
    _check_api_key()
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)

    enhanced = False
    result_profile = profile_data

    if req.enhance:
        try:
            llm_output = call_llm(profile_data.model_dump_json(), system=ATS_SYSTEM_PROMPT)
            cleaned = (
                llm_output.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            ats = ATSEnhancement(**json.loads(cleaned))
            result_profile = profile_data.model_copy(
                update={
                    "summary": ats.summary,
                    "work_experience": ats.work_experience,
                }
            )
            enhanced = True
        except Exception:
            pass  # fallback to original profile on any error

    entry = GeneratedCV(
        enhanced=int(enhanced),
        profile_snapshot=result_profile.model_dump_json(),
        profile_id=req.profile_id,
    )
    db.add(entry)
    db.commit()

    return GenerateCvResponse(enhanced=enhanced, profile=result_profile)
```

- [ ] Replace the full `generate_cover_letter` function with this:
```python
@router.post("/generate/cover-letter", response_model=CoverLetterResponse)
def generate_cover_letter(req: CoverLetterRequest, db: Session = Depends(get_db)):
    _check_api_key()
    profile = _get_profile_or_404(db, req.profile_id)
    profile_data = profile_to_schema(profile)

    prompt = f"""Candidate profile: {profile_data.model_dump_json()}
Job description: {req.job_description}
Additional context: {req.extra_context or "None"}"""

    try:
        text = call_llm(prompt, system=COVER_LETTER_SYSTEM_PROMPT)
    except APIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=400, detail={"detail": str(e), "code": "API_KEY_NOT_CONFIGURED"}
        ) from e
    except LLMCallError as e:
        raise HTTPException(
            status_code=502, detail={"detail": str(e), "code": "LLM_CALL_FAILED"}
        ) from e

    entry = GeneratedCoverLetter(
        company_name=req.company_name,
        job_description=req.job_description,
        extra_context=req.extra_context or None,
        cover_letter_text=text,
        profile_id=req.profile_id,
    )
    db.add(entry)
    db.commit()

    return CoverLetterResponse(cover_letter_text=text)
```

- [ ] Commit:
```bash
rtk git add app/routes/generate.py
rtk git commit -m "feat: generate routes accept profile_id, save to history"
```

---

### Task 7: Update history.py — join profile for badge fields

**Files:**
- Modify: `backend/app/routes/history.py`

- [ ] Read `backend/app/routes/history.py`.

- [ ] Update imports to add `Profile`:
```python
from app.models import GeneratedCV, GeneratedCoverLetter, Profile
```

- [ ] Add a helper to enrich a history entry with profile identity fields:
```python
def _enrich_cv(entry: GeneratedCV, db: Session) -> dict:
    d = {
        "id": entry.id,
        "created_at": entry.created_at,
        "enhanced": bool(entry.enhanced),
        "profile_snapshot": entry.profile_snapshot,
        "profile_id": entry.profile_id,
        "profile_label": None,
        "profile_color": None,
        "profile_icon": None,
    }
    if entry.profile_id:
        p = db.query(Profile).filter_by(id=entry.profile_id).first()
        if p:
            d["profile_label"] = p.label
            d["profile_color"] = p.color
            d["profile_icon"] = p.icon
    return d


def _enrich_cl(entry: GeneratedCoverLetter, db: Session) -> dict:
    d = {
        "id": entry.id,
        "created_at": entry.created_at,
        "company_name": entry.company_name,
        "job_description": entry.job_description,
        "extra_context": entry.extra_context,
        "cover_letter_text": entry.cover_letter_text,
        "profile_id": entry.profile_id,
        "profile_label": None,
        "profile_color": None,
        "profile_icon": None,
    }
    if entry.profile_id:
        p = db.query(Profile).filter_by(id=entry.profile_id).first()
        if p:
            d["profile_label"] = p.label
            d["profile_color"] = p.color
            d["profile_icon"] = p.icon
    return d
```

- [ ] Update list endpoints to use enriched dicts:
```python
@router.get("/history/cv", response_model=GeneratedCVListResponse)
def list_cv_history(db: Session = Depends(get_db)):
    items = db.query(GeneratedCV).order_by(GeneratedCV.created_at.desc()).all()
    return GeneratedCVListResponse(items=[_enrich_cv(e, db) for e in items])


@router.get("/history/cover-letter", response_model=GeneratedCoverLetterListResponse)
def list_cover_letter_history(db: Session = Depends(get_db)):
    items = db.query(GeneratedCoverLetter).order_by(GeneratedCoverLetter.created_at.desc()).all()
    return GeneratedCoverLetterListResponse(items=[_enrich_cl(e, db) for e in items])
```

- [ ] Update single-entry GET endpoints similarly:
```python
@router.get("/history/cv/{entry_id}", response_model=GeneratedCVEntry)
def get_cv_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCV).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return _enrich_cv(entry, db)


@router.get("/history/cover-letter/{entry_id}", response_model=GeneratedCoverLetterEntry)
def get_cover_letter_history_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneratedCoverLetter).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail={"detail": "Not found", "code": "NOT_FOUND"})
    return _enrich_cl(entry, db)
```

- [ ] Commit:
```bash
rtk git add app/routes/history.py
rtk git commit -m "feat: history routes join profile for label/color/icon fields"
```

---

### Task 8: Register profiles router + run Alembic migration

**Files:**
- Modify: `backend/main.py`
- Create: `backend/migrations/versions/<hash>_add_multi_profile_support.py` (auto-generated)

- [ ] Read `backend/main.py`.

- [ ] Add `profiles` to the routes import:
```python
from app.routes import generate, history, import_cv, profile, profiles
```

- [ ] Register the router (add alongside others):
```python
app.include_router(profiles.router, prefix="/api")
```

- [ ] Commit main.py:
```bash
rtk git add main.py
rtk git commit -m "feat: register profiles router"
```

- [ ] Generate the Alembic migration:
```bash
cd backend
uv run alembic revision --autogenerate -m "add multi profile support"
```
Expected: new file under `migrations/versions/`.

- [ ] Open the generated migration file. Verify `upgrade()` contains:
  - `op.add_column('profile', sa.Column('label', sa.String(), nullable=False, server_default='Default'))`
  - `op.add_column('profile', sa.Column('color', sa.String(), nullable=False, server_default='#6366f1'))`
  - `op.add_column('profile', sa.Column('icon', sa.String(), nullable=False, server_default='💼'))`
  - `op.add_column('generated_cv', sa.Column('profile_id', sa.Integer(), nullable=True))`
  - `op.add_column('generated_cover_letter', sa.Column('profile_id', sa.Integer(), nullable=True))`

  If Alembic did not generate `server_default` values for the new NOT NULL columns, add them manually:
  ```python
  op.add_column('profile', sa.Column('label', sa.String(), nullable=False, server_default='Default'))
  op.add_column('profile', sa.Column('color', sa.String(), nullable=False, server_default='#6366f1'))
  op.add_column('profile', sa.Column('icon', sa.String(), nullable=False, server_default='💼'))
  ```

- [ ] Apply the migration:
```bash
uv run alembic upgrade head
```
Expected: `Running upgrade ... -> ..., add multi profile support`

- [ ] Verify routes:
```bash
uv run python -c "from main import app; [print(r.path) for r in app.routes if 'profile' in r.path]"
```
Expected output includes: `/api/profiles`, `/api/profiles/{profile_id}`

- [ ] Commit:
```bash
rtk git add migrations/
rtk git commit -m "feat: alembic migration for multi-profile support"
```

---

## Chunk 2: Frontend — Stores, Types, API, Components

### Task 9: Update types.ts and api.ts

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] Read `frontend/src/lib/types.ts`.

- [ ] In `types.ts`, update `ProfileData` interface to add new optional fields at the top:
```typescript
export interface ProfileData {
  id?: number | null;
  label?: string;
  color?: string;
  icon?: string;
  name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  linkedin?: string | null;
  github?: string | null;
  portfolio?: string | null;
  summary?: string | null;
  work_experience?: WorkExperience[];
  education?: Education[];
  skills?: string[];
  projects?: Project[];
  certifications?: Certification[];
  updated_at?: string | null;
}
```

- [ ] Add new interfaces (append after existing ProfileData-related types):
```typescript
export interface ProfileListItem {
  id: number;
  label: string;
  color: string;
  icon: string;
  name: string;
}

export interface ProfileListResponse {
  items: ProfileListItem[];
}

export interface CreateProfileRequest {
  label: string;
  color: string;
  icon: string;
  clone_from_id?: number | null;
}

export interface GenerateCvRequest {
  profile_id: number;
  enhance?: boolean;
}
```

- [ ] Update `CoverLetterRequest` to add `profile_id`:
```typescript
export interface CoverLetterRequest {
  profile_id: number;
  job_description: string;
  company_name?: string | null;
  extra_context?: string;
}
```

- [ ] Update history entry interfaces to add profile badge fields:
```typescript
export interface GeneratedCVEntry {
  id: number;
  created_at: string;
  enhanced: boolean;
  profile_snapshot: string;
  profile_id?: number | null;
  profile_label?: string | null;
  profile_color?: string | null;
  profile_icon?: string | null;
}

export interface GeneratedCoverLetterEntry {
  id: number;
  created_at: string;
  company_name: string | null;
  job_description: string;
  extra_context: string | null;
  cover_letter_text: string;
  profile_id?: number | null;
  profile_label?: string | null;
  profile_color?: string | null;
  profile_icon?: string | null;
}
```

- [ ] Read `frontend/src/lib/api.ts`.

- [ ] In `api.ts`, replace `getProfile` and `saveProfile` (old single-profile functions) with:
```typescript
export const listProfiles = () =>
  request<ProfileListResponse>('/profiles');

export const createProfile = (data: CreateProfileRequest) =>
  request<ProfileData>('/profiles', { method: 'POST', body: JSON.stringify(data) });

export const getProfile = (profileId: number) =>
  request<ProfileData>(`/profiles/${profileId}`);

export const saveProfile = (profileId: number, data: ProfileData) =>
  request<ProfileData>(`/profiles/${profileId}`, { method: 'PUT', body: JSON.stringify(data) });

export const deleteProfile = (profileId: number) =>
  request<void>(`/profiles/${profileId}`, { method: 'DELETE' });
```

- [ ] Update `generateCv` to accept `GenerateCvRequest`:
```typescript
export const generateCv = (data: GenerateCvRequest) =>
  request<GenerateCvResponse>('/generate/cv', { method: 'POST', body: JSON.stringify(data) });
```

- [ ] Update `generateCoverLetter` — `CoverLetterRequest` already has `profile_id` from the type update above; no signature change needed, just ensure `profile_id` is passed through (it will be via the updated type).

- [ ] Merge these new types into the existing `import type { ... } from './types'` block at the top of `api.ts`. Do not replace the existing imports — add these alongside them:
```
ProfileListItem, ProfileListResponse, CreateProfileRequest, GenerateCvRequest
```

- [ ] Run type-check:
```bash
cd frontend
bun run check
```
Expected: 0 errors (warnings from unrelated files are fine).

- [ ] Commit:
```bash
cd frontend
rtk git add src/lib/types.ts src/lib/api.ts
rtk git commit -m "feat: types and API client for multi-profile"
```

---

### Task 10: Create Svelte stores

**Files:**
- Create: `frontend/src/lib/profiles.svelte.ts`
- Create: `frontend/src/lib/activeProfile.svelte.ts`

- [ ] Create `frontend/src/lib/profiles.svelte.ts`:
```typescript
import type { ProfileListItem } from './types';

function createProfilesStore() {
  let list = $state<ProfileListItem[]>([]);
  return {
    get all() { return list; },
    set(items: ProfileListItem[]) { list = items; },
    remove(id: number) { list = list.filter((p) => p.id !== id); },
    upsert(item: ProfileListItem) {
      const idx = list.findIndex((p) => p.id === item.id);
      if (idx >= 0) list[idx] = item;
      else list = [...list, item];
    },
  };
}

export const profiles = createProfilesStore();
```

- [ ] Create `frontend/src/lib/activeProfile.svelte.ts`:
```typescript
import { browser } from '$app/environment';

export type ActiveProfile = {
  id: number;
  label: string;
  color: string;
  icon: string;
};

function createActiveProfile() {
  let profile = $state<ActiveProfile | null>(null);

  return {
    get current() { return profile; },
    set(p: ActiveProfile) {
      profile = p;
      if (browser) localStorage.setItem('activeProfile', JSON.stringify(p));
    },
    initFromStorage(fallback: ActiveProfile | null) {
      if (!browser) { profile = fallback; return; }
      const stored = localStorage.getItem('activeProfile');
      if (stored) {
        try { profile = JSON.parse(stored) as ActiveProfile; return; }
        catch { /* fall through */ }
      }
      profile = fallback;
      if (fallback) localStorage.setItem('activeProfile', JSON.stringify(fallback));
    },
    clear() {
      profile = null;
      if (browser) localStorage.removeItem('activeProfile');
    },
  };
}

export const activeProfile = createActiveProfile();
```

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/lib/profiles.svelte.ts src/lib/activeProfile.svelte.ts
rtk git commit -m "feat: profiles and activeProfile Svelte 5 stores"
```

---

### Task 11: Create ProfileModal component

**Files:**
- Create: `frontend/src/lib/components/ProfileModal.svelte`

- [ ] Create `frontend/src/lib/components/ProfileModal.svelte`:
```svelte
<script lang="ts">
  import { createProfile, saveProfile, listProfiles } from '$lib/api';
  import type { ProfileData, CreateProfileRequest } from '$lib/types';
  import { profiles } from '$lib/profiles.svelte';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';

  type Mode = 'create' | 'edit';

  type Props = {
    mode: Mode;
    profile?: ProfileData | null;   // required in edit mode
    onclose: () => void;
    onsaved?: () => void;
  };

  let { mode, profile = null, onclose, onsaved }: Props = $props();

  const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6'];
  const ICONS  = ['💼', '🏢', '🎨', '💻', '🚀', '⚡', '🎯', '🌟'];

  let label = $state(profile?.label ?? '');
  let color = $state(profile?.color ?? COLORS[0]);
  let icon  = $state(profile?.icon  ?? ICONS[0]);
  let cloneEnabled = $state(false);
  let cloneFromId  = $state<number | null>(null);
  let saving = $state(false);
  let error  = $state('');

  const allProfiles = $derived(profiles.all);

  async function handleSubmit() {
    if (!label.trim()) { error = 'Label is required'; return; }
    saving = true;
    error = '';
    try {
      if (mode === 'create') {
        const req: CreateProfileRequest = {
          label: label.trim(),
          color,
          icon,
          clone_from_id: cloneEnabled ? cloneFromId : null,
        };
        const created = await createProfile(req);
        const fresh = await listProfiles();
        profiles.set(fresh.items);
        if (created.id) {
          activeProfile.set({ id: created.id, label: created.label ?? label, color: created.color ?? color, icon: created.icon ?? icon });
        }
      } else if (mode === 'edit' && profile?.id) {
        const updated = await saveProfile(profile.id, { ...profile, label: label.trim(), color, icon });
        profiles.upsert({ id: profile.id, label: updated.label ?? label, color: updated.color ?? color, icon: updated.icon ?? icon, name: updated.name });
        const ap = activeProfile.current;
        if (ap?.id === profile.id) {
          activeProfile.set({ id: profile.id, label: updated.label ?? label, color: updated.color ?? color, icon: updated.icon ?? icon });
        }
      }
      onsaved?.();
      onclose();
    } catch (e: any) {
      error = e.message ?? 'Something went wrong';
    } finally {
      saving = false;
    }
  }
</script>

<!-- Backdrop -->
<div
  class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
  onclick={onclose}
>
  <!-- Modal -->
  <div
    class="bg-card border rounded-xl shadow-xl p-6 w-full max-w-sm mx-4 space-y-5"
    onclick={(e) => e.stopPropagation()}
  >
    <h2 class="text-lg font-semibold">{mode === 'create' ? 'New Profile' : 'Edit Identity'}</h2>

    <!-- Label -->
    <div class="space-y-2">
      <Label for="profile-label">Label</Label>
      <Input id="profile-label" bind:value={label} placeholder="e.g. Software Engineer" />
    </div>

    <!-- Color -->
    <div class="space-y-2">
      <Label>Color</Label>
      <div class="flex gap-2 flex-wrap">
        {#each COLORS as c}
          <button
            type="button"
            onclick={() => color = c}
            class="w-7 h-7 rounded-full transition-transform hover:scale-110"
            style="background:{c}; outline: {color === c ? '3px solid currentColor' : 'none'}; outline-offset: 2px;"
            title={c}
          ></button>
        {/each}
      </div>
    </div>

    <!-- Icon -->
    <div class="space-y-2">
      <Label>Icon</Label>
      <div class="flex gap-2 flex-wrap">
        {#each ICONS as ic}
          <button
            type="button"
            onclick={() => icon = ic}
            class="w-9 h-9 rounded-lg border text-lg flex items-center justify-center transition-colors
              {icon === ic ? 'border-primary bg-primary/10' : 'border-border hover:bg-accent'}"
          >{ic}</button>
        {/each}
      </div>
    </div>

    <!-- Preview -->
    <div class="flex items-center gap-2 text-sm">
      <span>Preview:</span>
      <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border font-medium text-sm" style="border-color:{color}">
        <span class="w-2 h-2 rounded-full inline-block" style="background:{color}"></span>
        {icon} {label || 'Profile'}
      </span>
    </div>

    <!-- Clone (create mode only) -->
    {#if mode === 'create' && allProfiles.length > 0}
      <div class="space-y-2">
        <label class="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" bind:checked={cloneEnabled} class="rounded" />
          Copy data from existing profile
        </label>
        {#if cloneEnabled}
          <select
            bind:value={cloneFromId}
            class="w-full border rounded-md px-3 py-2 text-sm bg-background"
          >
            <option value={null}>— select profile —</option>
            {#each allProfiles as p}
              <option value={p.id}>{p.icon} {p.label} ({p.name})</option>
            {/each}
          </select>
        {/if}
      </div>
    {/if}

    {#if error}
      <p class="text-sm text-destructive">{error}</p>
    {/if}

    <div class="flex gap-2 justify-end pt-1">
      <Button variant="outline" onclick={onclose} disabled={saving}>Cancel</Button>
      <Button onclick={handleSubmit} disabled={saving}>
        {saving ? 'Saving…' : mode === 'create' ? 'Create Profile' : 'Save'}
      </Button>
    </div>
  </div>
</div>
```

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/lib/components/ProfileModal.svelte
rtk git commit -m "feat: ProfileModal component (create/edit with color, icon, clone)"
```

---

### Task 12: Create ProfileSwitcher component

**Files:**
- Create: `frontend/src/lib/components/ProfileSwitcher.svelte`

- [ ] Create `frontend/src/lib/components/ProfileSwitcher.svelte`:
```svelte
<script lang="ts">
  import { profiles } from '$lib/profiles.svelte';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import ProfileModal from './ProfileModal.svelte';

  let dropdownOpen = $state(false);
  let modalMode = $state<'create' | 'edit' | null>(null);

  const ap = $derived(activeProfile.current);
  const allProfiles = $derived(profiles.all);

  function switchProfile(p: { id: number; label: string; color: string; icon: string }) {
    activeProfile.set(p);
    dropdownOpen = false;
  }

  function openCreate() {
    dropdownOpen = false;
    modalMode = 'create';
  }

  function openEdit() {
    dropdownOpen = false;
    modalMode = 'edit';
  }

  function closeModal() {
    modalMode = null;
  }
</script>

<div class="relative">
  <!-- Trigger button -->
  <button
    onclick={() => dropdownOpen = !dropdownOpen}
    class="flex items-center gap-2 border rounded-lg px-3 py-2 text-sm font-medium bg-background shadow-sm hover:bg-accent transition-colors min-w-[160px] justify-between"
  >
    <span class="flex items-center gap-2">
      {#if ap}
        <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background:{ap.color}"></span>
        <span class="text-base leading-none">{ap.icon}</span>
        <span class="truncate">{ap.label}</span>
      {:else}
        <span class="text-muted-foreground">No profile</span>
      {/if}
    </span>
    <span class="text-muted-foreground text-xs ml-1">▼</span>
  </button>

  <!-- Dropdown -->
  {#if dropdownOpen}
    <!-- Click-outside backdrop -->
    <div class="fixed inset-0 z-10" onclick={() => dropdownOpen = false}></div>

    <div class="absolute top-full mt-1 left-0 z-20 bg-card border rounded-lg shadow-lg py-1 min-w-[200px]">
      {#each allProfiles as p}
        <button
          onclick={() => p.id === ap?.id ? openEdit() : switchProfile(p)}
          class="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
        >
          <span class="w-2 h-2 rounded-full shrink-0" style="background:{p.color}"></span>
          <span>{p.icon}</span>
          <span class="truncate flex-1">{p.label}</span>
          {#if p.id === ap?.id}
            <span class="text-xs text-muted-foreground">active</span>
          {/if}
        </button>
      {/each}

      <div class="border-t my-1"></div>
      <button
        onclick={openCreate}
        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
      >
        <span class="text-base">＋</span> New Profile
      </button>
    </div>
  {/if}
</div>

<!-- Modals -->
{#if modalMode === 'create'}
  <ProfileModal mode="create" onclose={closeModal} />
{:else if modalMode === 'edit' && ap}
  {#await import('$lib/api').then(m => m.getProfile(ap.id)) then profileData}
    <ProfileModal mode="edit" profile={profileData} onclose={closeModal} />
  {/await}
{/if}
```

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/lib/components/ProfileSwitcher.svelte
rtk git commit -m "feat: ProfileSwitcher dropdown component"
```

---

## Chunk 3: Frontend — Layout and Pages

### Task 13: Update +layout.ts

**Files:**
- Modify: `frontend/src/routes/+layout.ts`

- [ ] Read `frontend/src/routes/+layout.ts`.

- [ ] Replace the entire file with:
```typescript
import { redirect } from '@sveltejs/kit';
import { getOnboardingStatus, listProfiles } from '$lib/api';
import { profiles } from '$lib/profiles.svelte';
import { activeProfile } from '$lib/activeProfile.svelte';

export const ssr = false;

export const load = async ({ url }) => {
  let isOnboarded = true;

  try {
    const status = await getOnboardingStatus();
    isOnboarded = status.is_onboarded;

    if (isOnboarded) {
      try {
        const res = await listProfiles();
        profiles.set(res.items);

        // Validate stored active profile or fall back to first
        const stored = typeof localStorage !== 'undefined'
          ? localStorage.getItem('activeProfile')
          : null;
        let storedProfile = stored ? JSON.parse(stored) : null;
        const validStored = storedProfile && res.items.some((p) => p.id === storedProfile.id);
        const fallback = res.items[0]
          ? { id: res.items[0].id, label: res.items[0].label, color: res.items[0].color, icon: res.items[0].icon }
          : null;
        activeProfile.initFromStorage(validStored ? storedProfile : fallback);
      } catch (e) {
        console.warn('Could not load profiles', e);
      }
    }

    if (url.pathname.startsWith('/onboarding')) return { isOnboarded };
    if (!isOnboarded) {
      if (url.pathname.startsWith('/profile')) return { isOnboarded };
      throw redirect(307, '/onboarding');
    }
  } catch (err: any) {
    if (err?.status === 307) throw err;
    console.warn('Could not check onboarding status. Allowing navigation.', err);
  }

  return { isOnboarded };
};
```

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/routes/+layout.ts
rtk git commit -m "feat: layout loads profiles list, initializes active profile store"
```

---

### Task 14: Update +layout.svelte — add Profiles nav link

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] Read `frontend/src/routes/+layout.svelte`.

- [ ] Find the `navLinks` array and add `{ href: '/profiles', label: 'Profiles' }` before History:
```typescript
const navLinks = [
  { href: '/', label: 'Dashboard' },
  { href: '/profile', label: 'Profile' },
  { href: '/generate', label: 'Generate CV' },
  { href: '/cover-letter', label: 'Cover Letter' },
  { href: '/profiles', label: 'Profiles' },
  { href: '/history', label: 'History' },
];
```

- [ ] Run type-check:
```bash
bun run check
```

- [ ] Commit:
```bash
rtk git add src/routes/+layout.svelte
rtk git commit -m "feat: add Profiles link to nav"
```

---

### Task 15: Create /profiles management page

**Files:**
- Create: `frontend/src/routes/profiles/+page.svelte`

- [ ] Create `frontend/src/routes/profiles/+page.svelte`:
```svelte
<script lang="ts">
  import { deleteProfile, getProfile, listProfiles } from '$lib/api';
  import { profiles } from '$lib/profiles.svelte';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import ProfileModal from '$lib/components/ProfileModal.svelte';
  import type { ProfileListItem } from '$lib/types';
  import { Button } from '$lib/components/ui/button';
  import { goto } from '$app/navigation';

  let modalMode = $state<'create' | 'edit' | null>(null);
  let editingProfile = $state<ProfileListItem | null>(null);
  let deletingId = $state<number | null>(null);
  let error = $state('');

  const allProfiles = $derived(profiles.all);

  function openCreate() { modalMode = 'create'; editingProfile = null; }
  function openEdit(p: ProfileListItem) { editingProfile = p; modalMode = 'edit'; }
  function closeModal() { modalMode = null; editingProfile = null; }

  async function handleDelete(p: ProfileListItem) {
    if (!confirm(`Delete profile "${p.label}"? This cannot be undone.`)) return;
    deletingId = p.id;
    error = '';
    try {
      await deleteProfile(p.id);
      profiles.remove(p.id);
      const ap = activeProfile.current;
      if (ap?.id === p.id) {
        const remaining = profiles.all;
        if (remaining.length > 0) {
          activeProfile.set({ id: remaining[0].id, label: remaining[0].label, color: remaining[0].color, icon: remaining[0].icon });
        } else {
          activeProfile.clear();
          goto('/onboarding');
          return;
        }
      }
    } catch (e: any) {
      error = e.message ?? 'Could not delete profile';
    } finally {
      deletingId = null;
    }
  }

  async function handleSaved() {
    const res = await listProfiles();
    profiles.set(res.items);
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold">Profiles</h1>
    <Button onclick={openCreate}>＋ New Profile</Button>
  </div>

  {#if error}
    <p class="text-sm text-destructive">{error}</p>
  {/if}

  {#if allProfiles.length === 0}
    <p class="text-muted-foreground">No profiles yet.</p>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each allProfiles as p}
        <div class="border rounded-xl p-5 bg-card space-y-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center text-2xl" style="background:{p.color}20; border: 1.5px solid {p.color}">
              {p.icon}
            </div>
            <div>
              <div class="font-semibold text-sm">{p.label}</div>
              <div class="text-xs text-muted-foreground">{p.name || 'No name set'}</div>
            </div>
            {#if activeProfile.current?.id === p.id}
              <span class="ml-auto text-xs px-2 py-0.5 rounded-full border font-medium" style="border-color:{p.color};color:{p.color}">active</span>
            {/if}
          </div>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" class="flex-1" onclick={() => openEdit(p)}>Edit</Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={deletingId === p.id}
              onclick={() => handleDelete(p)}
            >
              {deletingId === p.id ? '…' : 'Delete'}
            </Button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if modalMode === 'create'}
  <ProfileModal mode="create" onclose={closeModal} onsaved={handleSaved} />
{:else if modalMode === 'edit' && editingProfile}
  {#await getProfile(editingProfile.id) then fullProfile}
    <ProfileModal mode="edit" profile={fullProfile} onclose={closeModal} onsaved={handleSaved} />
  {/await}
{/if}
```

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/routes/profiles/+page.svelte
rtk git commit -m "feat: /profiles management page"
```

---

### Task 16: Add ProfileSwitcher to profile, generate, cover-letter pages

**Files:**
- Modify: `frontend/src/routes/profile/+page.svelte`
- Modify: `frontend/src/routes/generate/+page.svelte`
- Modify: `frontend/src/routes/cover-letter/+page.svelte`

**profile/+page.svelte:**
- [ ] Read `frontend/src/routes/profile/+page.svelte`.
- [ ] Add these two imports in the `<script>` block (alongside existing imports):
  ```typescript
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import { activeProfile } from '$lib/activeProfile.svelte';
  ```
- [ ] Remove `import { onMount } from 'svelte';` only if `onMount` is not used anywhere else in the file (search for other `onMount(` calls before deleting).
- [ ] Replace the existing `loadProfile` function (currently calls `getProfile()` with no args and reads `res.profile`) with a version that takes an id and reads the response directly:
  ```typescript
  async function loadProfile(id: number) {
    loading = true;
    try {
      const data = await getProfile(id);
      profile = { ...data };
      skillsText = '';
    } catch (e: any) {
      toastState.error(`Failed to load profile: ${e.message}`);
    } finally {
      loading = false;
    }
  }
  ```
- [ ] Replace `onMount(loadProfile)` with a `$effect` that reacts to the active profile (this handles both initial load and profile switching):
  ```typescript
  $effect(() => {
    const ap = activeProfile.current;
    if (ap) loadProfile(ap.id);
  });
  ```
- [ ] Update `handleSave` to pass the active profile ID (currently calls `saveProfile(profile)` with no ID):
  ```typescript
  async function handleSave() {
    const ap = activeProfile.current;
    if (!ap) return;
    saving = true;
    try {
      await saveProfile(ap.id, profile);
      toastState.success('Profile saved successfully!');
      await invalidateAll();
    } catch (e: any) {
      toastState.error(`Save failed: ${e.message}`);
    } finally {
      saving = false;
    }
  }
  ```
- [ ] Update `onImportSuccess` to reload using the active profile ID (currently calls `loadProfile()` with no args):
  ```typescript
  async function onImportSuccess() {
    showImporter = false;
    const ap = activeProfile.current;
    if (ap) await loadProfile(ap.id);
    await invalidateAll();
  }
  ```
- [ ] Add `<ProfileSwitcher />` at the very top of the template (before the page heading).

**generate/+page.svelte:**
- [ ] Read `frontend/src/routes/generate/+page.svelte`.
- [ ] Add `ProfileSwitcher` import and `activeProfile` import.
- [ ] Add `<ProfileSwitcher />` at top of template.
- [ ] Update the `generateCv` call to pass `profile_id`. Note: Task 9 already updated `generateCv` in `api.ts` to accept `GenerateCvRequest`. Add a null guard at the top of `handleGenerate`:
  ```typescript
  async function handleGenerate() {
    const ap = activeProfile.current;
    if (!ap) return;
    loading = true;
    profile = null;
    try {
      const res = await generateCv({ profile_id: ap.id, enhance: true });
      ...
  ```
  Replace only the `const res = await generateCv()` line with `const res = await generateCv({ profile_id: ap.id, enhance: true });` and add the `const ap = activeProfile.current; if (!ap) return;` lines at the top of the function body (before `loading = true`).

**cover-letter/+page.svelte:**
- [ ] Read `frontend/src/routes/cover-letter/+page.svelte`.
- [ ] Add `ProfileSwitcher` import and `activeProfile` import.
- [ ] Add `<ProfileSwitcher />` at top of template.
- [ ] Update the `generateCoverLetter` call to pass `profile_id`. Add a null guard at the top of the generate handler, consistent with the generate page:
  ```typescript
  const ap = activeProfile.current;
  if (!ap) return;
  // ... then use ap.id:
  const res = await generateCoverLetter({
    profile_id: ap.id,
    job_description: jobDescription,
    company_name: companyName.trim() || null,
    extra_context: extraContext,
  });
  ```

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/routes/profile/+page.svelte src/routes/generate/+page.svelte src/routes/cover-letter/+page.svelte
rtk git commit -m "feat: add ProfileSwitcher to profile, generate, cover-letter pages"
```

---

### Task 17: Update history page — show profile badge

**Files:**
- Modify: `frontend/src/routes/history/+page.svelte`

- [ ] Read `frontend/src/routes/history/+page.svelte`.

Note: Task 9 already added `profile_id`, `profile_label`, `profile_color`, and `profile_icon` fields to `GeneratedCVEntry` and `GeneratedCoverLetterEntry` in `types.ts`. These fields are the ones referenced below.

- [ ] In the CV list, find the `<div class="flex items-center justify-between gap-2">` inside each entry button and insert the profile badge after the existing `{#if entry.enhanced}` / `{:else}` badge block:
```svelte
<div class="flex items-center justify-between gap-2">
  <span class="text-sm font-medium truncate">{formatDate(entry.created_at)}</span>
  <div class="flex items-center gap-1.5 shrink-0">
    {#if entry.profile_color && entry.profile_icon}
      <span class="flex items-center gap-1 text-xs text-muted-foreground">
        <span class="w-2 h-2 rounded-full" style="background:{entry.profile_color}"></span>
        {entry.profile_icon}
      </span>
    {/if}
    {#if entry.enhanced}
      <Badge variant="default" class="text-xs">AI</Badge>
    {:else}
      <Badge variant="secondary" class="text-xs">Raw</Badge>
    {/if}
  </div>
</div>
```

- [ ] In the cover letter list, insert the profile badge between the company name `<div>` and the date `<div>` inside each entry button:
```svelte
<div class="text-sm font-medium truncate">
  {entry.company_name ?? 'Unknown Company'}
</div>
{#if entry.profile_color && entry.profile_icon}
  <span class="flex items-center gap-1 text-xs text-muted-foreground">
    <span class="w-2 h-2 rounded-full" style="background:{entry.profile_color}"></span>
    {entry.profile_icon}
  </span>
{/if}
<div class="text-xs text-muted-foreground mt-0.5">{formatDate(entry.created_at)}</div>
```

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Run final smoke test:
```bash
cd backend
uv run python -c "
from main import app
paths = [r.path for r in app.routes]
assert '/api/profiles' in paths, 'profiles list missing'
assert '/api/profiles/{profile_id}' in paths, 'profiles get missing'
print('All profile routes present:', [p for p in paths if 'profile' in p])
"
```

- [ ] Commit:
```bash
cd frontend
rtk git add src/routes/history/+page.svelte
rtk git commit -m "feat: show profile badge on history entries"
```

---

## Summary

After all tasks the full flow is:

1. App loads → `+layout.ts` fetches profiles list → initializes `profiles` store + `activeProfile` from localStorage
2. User visits `/profiles` → can create (blank or clone), edit identity (label/color/icon), delete profiles
3. User visits Generate CV → `ProfileSwitcher` shows active profile, user can switch → generate uses active `profile_id`
4. User visits Cover Letter → same pattern → cover letter tagged with `profile_id`
5. History page shows all generations with a color dot + icon badge indicating which profile produced them
