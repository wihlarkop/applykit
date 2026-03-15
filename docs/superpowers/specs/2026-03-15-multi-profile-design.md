# Multi-Profile Support — Design Spec

**Date:** 2026-03-15
**Status:** Approved
**Feature:** Allow users to maintain multiple professional identities (e.g. "Software Engineer" vs "Technical Manager"), each with its own full profile data, color, and icon. History is shared across all profiles but tagged with the profile that generated each entry.

---

## Goals

- Users can create, edit, clone, and delete profiles
- Each profile has a label, hex color, and emoji icon for visual identity
- An "active profile" is tracked in localStorage on the frontend; all generate/cover-letter actions use it
- Generated CV and cover letter history entries are tagged with the profile that created them
- The history page remains a single shared list, showing a color/icon badge per entry

## Non-Goals

- No authentication or per-user isolation (single-user app)
- No profile-specific settings (theme, LLM config, etc.)
- No export/import of individual profiles

---

## Data Model

### Profile table — new columns

```python
label = Column(String, nullable=False, default="Default")
color = Column(String, nullable=False, default="#6366f1")  # hex color
icon  = Column(String, nullable=False, default="💼")        # emoji
```

- `id` column: remove `default=1`, keep as `Integer, primary_key=True, autoincrement=True`
- Existing row (id=1) backfilled with defaults in migration

### GeneratedCV — new column

```python
profile_id = Column(Integer, ForeignKey("profile.id"), nullable=True)
```

### GeneratedCoverLetter — new column

```python
profile_id = Column(Integer, ForeignKey("profile.id"), nullable=True)
```

Nullable so existing history rows are unaffected.

---

## Backend API

All old `/api/profile` (GET/POST) endpoints are removed and replaced with the following clean resource.

### Profile resource

| Method | Endpoint | Body / Params | Response |
|--------|----------|---------------|----------|
| `GET` | `/api/profiles` | — | `ProfileListResponse` |
| `POST` | `/api/profiles` | `CreateProfileRequest` | `ProfileData` |
| `GET` | `/api/profiles/{id}` | — | `ProfileData` |
| `PUT` | `/api/profiles/{id}` | `ProfileData` | `ProfileData` |
| `DELETE` | `/api/profiles/{id}` | — | 204 |

**`GET /api/profiles`** returns lightweight list items (no work_experience etc.):
```python
class ProfileListItem(BaseModel):
    id: int
    label: str
    color: str
    icon: str
    name: str
```

**`POST /api/profiles`** — create blank or clone:
```python
class CreateProfileRequest(BaseModel):
    label: str
    color: str
    icon: str
    clone_from_id: int | None = None
```
If `clone_from_id` provided: copy all profile field data, assign new `label`/`color`/`icon`.

**`DELETE /api/profiles/{id}`** — guard: if only one profile exists, return `400 { "detail": "Cannot delete the last profile", "code": "LAST_PROFILE" }`.

### Updated generate routes

```python
class GenerateCvRequest(BaseModel):
    profile_id: int
    enhance: bool = True

class CoverLetterRequest(BaseModel):
    profile_id: int
    job_description: str
    company_name: str | None = None
    extra_context: str = ""
```

Both routes load the profile from DB using `profile_id`, generate content, and save history with `profile_id`.

### Onboarding endpoint

`GET /api/onboarding` — returns `is_onboarded: true` if at least one profile with a non-empty `name` exists (any id, not just id=1).

---

## Schemas

New / updated Pydantic schemas in `backend/app/schemas.py`:

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

`ProfileData` gains `label`, `color`, `icon`, `id` fields.

History schemas gain `profile_id: int | None` and `profile_label: str | None`, `profile_color: str | None`, `profile_icon: str | None` for display on the history page (joined at query time).

---

## Alembic Migration

Single migration `add_multi_profile_support`:

1. Add `label VARCHAR NOT NULL DEFAULT 'Default'` to `profile`
2. Add `color VARCHAR NOT NULL DEFAULT '#6366f1'` to `profile`
3. Add `icon VARCHAR NOT NULL DEFAULT '💼'` to `profile`
4. Make `profile.id` autoincrement (requires SQLite table recreation via `batch_alter_table`)
5. Add `profile_id INTEGER REFERENCES profile(id)` (nullable) to `generated_cv`
6. Add `profile_id INTEGER REFERENCES profile(id)` (nullable) to `generated_cover_letter`

---

## Frontend

### New files

| File | Purpose |
|------|---------|
| `src/lib/activeProfile.svelte.ts` | Svelte 5 `$state` store — active profile, persisted to localStorage |
| `src/lib/components/ProfileSwitcher.svelte` | Dropdown button showing active profile; lists all profiles; opens create modal |
| `src/lib/components/ProfileModal.svelte` | Create/edit modal — label input, 8 color swatches, 8 icon tiles, clone option, live preview |
| `src/routes/profiles/+page.svelte` | Profile management page — list all profiles, edit/delete per card, New Profile button |

### Updated files

| File | Change |
|------|--------|
| `src/lib/types.ts` | Add `ProfileListItem`, `ProfileListResponse`, `CreateProfileRequest`, `GenerateCvRequest`; add `id`, `label`, `color`, `icon` to `ProfileData`; add `profile_id/label/color/icon` to history types |
| `src/lib/api.ts` | Add `listProfiles`, `createProfile`, `getProfile`, `saveProfile`, `deleteProfile`; update `generateCv`, `generateCoverLetter` to include `profile_id` |
| `src/routes/+layout.ts` | Fetch profiles list; initialize `activeProfile` store from localStorage or first profile |
| `src/routes/+layout.svelte` | Add "Profiles" nav link |
| `src/routes/profile/+page.svelte` | Add `<ProfileSwitcher />` at top; load/save by active `profile_id` |
| `src/routes/generate/+page.svelte` | Add `<ProfileSwitcher />` at top; pass `profile_id` in generate request |
| `src/routes/cover-letter/+page.svelte` | Add `<ProfileSwitcher />` at top; pass `profile_id` in cover letter request |
| `src/routes/history/+page.svelte` | Show color dot + icon badge on each history entry |

### `activeProfile.svelte.ts` design

```typescript
export type ActiveProfile = { id: number; label: string; color: string; icon: string };

function createActiveProfile() {
  let profile = $state<ActiveProfile | null>(null);
  // init from localStorage on browser
  return {
    get current() { return profile; },
    set(p: ActiveProfile) { profile = p; localStorage.setItem('activeProfile', JSON.stringify(p)); },
    clear() { profile = null; localStorage.removeItem('activeProfile'); }
  };
}
export const activeProfile = createActiveProfile();
```

### ProfileSwitcher component

- Renders a button: `[color dot] [icon] [label] ▼`
- On click: opens inline dropdown listing all profiles from `$profiles` store
- Each row: color dot + icon + label, click to switch active
- Bottom of dropdown: `＋ New Profile` → opens `ProfileModal` in create mode
- Clicking active profile row: opens `ProfileModal` in edit mode

### ProfileModal component

- **Label** text input
- **Color** — 8 swatches: `#6366f1` `#f59e0b` `#10b981` `#ef4444` `#3b82f6` `#8b5cf6` `#ec4899` `#14b8a6`
- **Icon** — 8 emoji tiles: `💼` `🏢` `🎨` `💻` `🚀` `⚡` `🎯` `🌟`
- **Clone toggle** (create mode only): checkbox "Copy data from existing profile" → profile select dropdown
- **Live preview badge**: shows selected icon + label with selected color dot
- Submit → `createProfile` or `saveProfile` API call; refreshes profiles list; sets new profile as active (on create)

### `/profiles` page

- Header: "Profiles" + "New Profile" button
- Grid of cards, one per profile
- Each card: large icon, label, name (from profile.name), color dot, Edit button, Delete button
- Delete: confirm dialog, disabled if last profile
- "Profiles" link added to nav (alongside History)

---

## Error Handling

- Delete last profile → `400 LAST_PROFILE` → show toast "Can't delete your only profile"
- Profile not found → `404 NOT_FOUND`
- `profile_id` in generate request points to deleted profile → `404` → frontend shows error

---

## Key Constraints

- No unit tests (project preference)
- `uv` for Python, `bun` for JavaScript
- SQLite with Alembic; use `batch_alter_table` for column changes on existing tables
- Svelte 5 runes (`$state`, `$derived`, `$props`, `$effect`) — no legacy stores
- Tailwind CSS v4, shadcn-svelte components
