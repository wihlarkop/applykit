# Onboarding Gate: API Key Required Before Profile Setup

**Date:** 2026-03-16
**Status:** Approved

## Problem

New users who open the app without a configured API key can reach the onboarding flow and attempt to use "Use AI Assistant" (CV import). The backend rejects the request with a 400 error but the UX provides no clear path forward — the user just sees a toast error with no guidance.

Additionally, there is no enforced ordering: configure AI → then set up profile. Users can land on onboarding without knowing they need to configure an API key first.

## Goal

Enforce a two-step gate before the user can use the app:
1. **Step 1:** Configure AI provider + API key (`/settings`)
2. **Step 2:** Upload CV or fill profile (`/onboarding`)

Nav remains completely hidden until both steps complete (existing behavior preserved).

---

## Architecture

### Gate logic in `+layout.ts`

Fetch `/api/status` and `/api/onboarding` in parallel. Add a new gate before the existing onboarding redirect:

```
if (!api_key_configured && !on /settings)
  → redirect to /settings

else if (!is_onboarded && !on /onboarding && !on /profile[/*] && !on /settings)
  → redirect to /onboarding

else
  → load app normally
```

Note: `/settings` is exempted from BOTH gates. A user who has set their API key but is not yet onboarded must still be able to navigate back to `/settings` to edit their key — bouncing them to `/onboarding` instead would be confusing.

The `getStatus()` call is added to the existing parallel load. The redirect exception list for the first gate: `/settings` only. No other pages are exempt.

**Error handling:** existing `try/catch` already swallows backend errors and allows navigation — this behavior is preserved. If `/api/status` fails, treat as configured (fail open) to avoid locking users out.

### `SettingsModal.svelte` — add `invalidateAll()` after save

After a successful save, call `invalidateAll()` from `$app/navigation`. This re-runs `+layout.ts`, which re-fetches `/api/status`, sees `api_key_configured = true`, and since `!is_onboarded`, automatically redirects to `/onboarding`. No manual navigation needed.

Remove the existing `settingsStore.notify()` call when inside `handleSave` — `invalidateAll()` already causes a full layout reload and redirect, making `notify()` a redundant in-flight re-fetch on a page about to be navigated away. Keep `settingsStore.notify()` only if the user saves from a context where they are already onboarded (i.e., editing settings after initial setup), since in that case there is no redirect and the settings page + SettingsButton need to refresh. Simplest implementation: keep `settingsStore.notify()` in all cases — the redundant call is harmless — and just add `invalidateAll()` after it.

The "don't count until saved" requirement is already guaranteed: the gate reads from the DB via `/api/status`, and the DB only updates on Save. A close or refresh without saving re-checks the DB and redirects back to `/settings`. Browser back button after redirect to `/onboarding` also returns to `/settings`, where the layout re-runs and redirects to `/onboarding` again — back navigation is intentionally a no-op during onboarding.

### `settings/+page.svelte` — step progress indicator

When the user arrives at `/settings` without being onboarded yet, show a subtle top banner:

```
Step 1 of 2 — Configure AI provider   →   Step 2 of 2 — Setup your profile
```

This requires `isApiKeyConfigured` and `isOnboarded` to be passed from layout data so the settings page knows its context. The banner is hidden once API key is saved (i.e., `isApiKeyConfigured === true`).

---

## Data Flow

```
App load
  └─ layout.ts: parallel fetch /api/status + /api/onboarding
       ├─ api_key_configured = false → redirect /settings
       ├─ api_key_configured = true, is_onboarded = false → redirect /onboarding
       └─ both true → load app normally

/settings page
  └─ user opens "Add Integration" modal
       ├─ fills provider + model + API key
       ├─ clicks Save → updateSettings() → DB updated
       │    └─ invalidateAll() → layout re-runs → redirect /onboarding
       └─ closes without saving → refresh re-checks DB → redirect back to /settings
```

---

## Changes Required

| File | Change |
|------|--------|
| `frontend/src/routes/+layout.ts` | Add parallel `getStatus()` fetch; add API key gate before existing onboarding gate; return `isApiKeyConfigured` in load result |
| `frontend/src/lib/components/SettingsModal.svelte` | Add `invalidateAll()` after successful save |
| `frontend/src/routes/settings/+page.svelte` | Accept `isApiKeyConfigured` + `isOnboarded` from layout data; show step progress banner when not yet onboarded |
| `frontend/src/routes/+layout.svelte` | Pass `isApiKeyConfigured` from `data` prop (minor, for settings page access) |

---

## What Does NOT Change

- Nav visibility logic (hidden when not onboarded) — unchanged
- Onboarding page and its steps — unchanged
- Manual setup path (`/profile`) — unchanged, still exempt from onboarding redirect
- All backend routes — no changes needed
- `SettingsButton.svelte` — unchanged
