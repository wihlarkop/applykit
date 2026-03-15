# Onboarding Gate Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce API key configuration before profile setup — redirect unauthenticated users to `/settings`, then to `/onboarding`, and show step progress on the settings page during this flow.

**Architecture:** All redirect logic lives in `+layout.ts` via two sequential gates. `SettingsModal` triggers `invalidateAll()` after save so the layout re-runs and redirects automatically. The settings page reads layout data via `$app/state` to show a contextual step banner.

**Tech Stack:** SvelteKit 2, Svelte 5 runes, `$app/navigation` (`invalidateAll`), `$app/state` (`page`)

**Spec:** `docs/superpowers/specs/2026-03-16-onboarding-gate-design.md`

---

## Chunk 1: Layout gate + modal redirect

### Task 1: Update `+layout.ts` — two-gate redirect logic

**Files:**
- Modify: `frontend/src/routes/+layout.ts`

Context: Currently fetches only `getOnboardingStatus()`. We add a parallel `getStatus()` fetch and introduce Gate 1 (API key) before the existing Gate 2 (onboarding). `/settings` is exempt from both gates so users can always navigate there.

Current imports line 3:
```typescript
import { getOnboardingStatus, listProfiles, createProfile } from '$lib/api';
```

Current gate logic lines 42–46:
```typescript
if (url.pathname.startsWith('/onboarding')) return { isOnboarded };
if (!isOnboarded) {
  if (url.pathname === '/profile' || url.pathname.startsWith('/profile/')) return { isOnboarded };
  throw redirect(307, '/onboarding');
}
```

Current return line 52:
```typescript
return { isOnboarded };
```

- [ ] Open `frontend/src/routes/+layout.ts`.

- [ ] Add `getStatus` to the import on line 3:
```typescript
import { getOnboardingStatus, getStatus, listProfiles, createProfile } from '$lib/api';
```

- [ ] Add `isApiKeyConfigured` declaration immediately after `let isOnboarded = true;` (line 10):
```typescript
let isOnboarded = true;
let isApiKeyConfigured = true; // fail open — if /api/status unreachable, don't lock users out
```

- [ ] Replace the `getOnboardingStatus()` call on line 13 — use assignment (not `const`) so the outer `let` default is the fallback on error:
```typescript
// Before:
const status = await getOnboardingStatus();
isOnboarded = status.is_onboarded;

// After:
const [onboarding, llmStatus] = await Promise.all([getOnboardingStatus(), getStatus()]);
isOnboarded = onboarding.is_onboarded;
isApiKeyConfigured = llmStatus.api_key_configured;
```

- [ ] Replace the gate logic (lines 42–46) with the two-gate version:
```typescript
const onSettings = url.pathname.startsWith('/settings');
const onOnboarding = url.pathname.startsWith('/onboarding');
const onProfile = url.pathname === '/profile' || url.pathname.startsWith('/profile/');

// Gate 1: API key must be configured
if (!isApiKeyConfigured && !onSettings) {
  throw redirect(307, '/settings');
}

// Gate 2: Profile must exist (onboarding)
if (!isOnboarded && !onSettings && !onOnboarding && !onProfile) {
  throw redirect(307, '/onboarding');
}
```

- [ ] Replace the final return on line 52 (and the early return inside the old gate — now removed):
```typescript
return { isOnboarded, isApiKeyConfigured };
```

- [ ] Run type-check:
```bash
cd frontend && bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
cd frontend && rtk git add src/routes/+layout.ts && rtk git commit -m "feat: add API key gate to layout — redirect to /settings before onboarding"
```

---

### Task 2: Update `SettingsModal.svelte` — trigger layout re-run after save

**Files:**
- Modify: `frontend/src/lib/components/SettingsModal.svelte`

Context: After a successful save, we need `invalidateAll()` to re-run `+layout.ts`. The layout will then see `api_key_configured = true`, detect `!isOnboarded`, and redirect to `/onboarding` automatically. `settingsStore.notify()` is kept — it's harmless and still needed when already-onboarded users edit settings (no redirect occurs in that path, so the settings page and SettingsButton still need to refresh).

Current `handleSave` success block (lines 96–99):
```typescript
await updateSettings({ model: selectedModel, api_key: keyToSave });
settingsStore.notify();
toastState.success('Settings saved successfully.');
open = false;
```

- [ ] Open `frontend/src/lib/components/SettingsModal.svelte`.

- [ ] Add `invalidateAll` to the script imports (line 1, after the existing imports):
```typescript
import { invalidateAll } from '$app/navigation';
```

- [ ] In `handleSave`, add `invalidateAll()` after `open = false`:
```typescript
await updateSettings({ model: selectedModel, api_key: keyToSave });
settingsStore.notify();
toastState.success('Settings saved successfully.');
open = false;
await invalidateAll();
```

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/lib/components/SettingsModal.svelte && rtk git commit -m "feat: invalidateAll after settings save — triggers layout re-check and redirect"
```

---

## Chunk 2: Settings page step banner

### Task 3: Update `settings/+page.svelte` — step progress banner

**Files:**
- Modify: `frontend/src/routes/settings/+page.svelte`

Context: When a user arrives at `/settings` without being onboarded yet, show a top banner indicating they are in a 2-step setup flow. The banner only shows when `!page.data.isOnboarded`. We use `page` from `$app/state` (Svelte 5's reactive page object) to read layout data without a `+page.ts`.

The banner has two states:
- `!page.data.isApiKeyConfigured`: Step 1 active (Configure AI), Step 2 pending (Setup profile)
- `page.data.isApiKeyConfigured && !page.data.isOnboarded`: Step 1 done, Step 2 pending — user navigated back to settings

- [ ] Open `frontend/src/routes/settings/+page.svelte`.

- [ ] Add `page` import to the script block (after existing imports):
```typescript
import { page } from '$app/state';
```
Note: `$app/state` (not `$app/stores`) is the correct import for Svelte 5 runes files. It exposes `page` as a plain reactive object — use `page.data.*` directly, no `$` prefix needed. This file already uses runes (`$state`, `$effect`) so this is the right module to use here.

- [ ] Add `ChevronRight` to the existing lucide import:
```typescript
import { CircleAlert, CircleCheck, ChevronRight, Cpu, Pencil, Plus, Settings } from '@lucide/svelte';
```

- [ ] Insert the step banner between the closing `</script>` tag and the opening `<div class="max-w-2xl space-y-6">`. Add it as a wrapping div:

Replace:
```svelte
<div class="max-w-2xl space-y-6">
```
with:
```svelte
<div class="max-w-2xl space-y-6">
  {#if !page.data.isOnboarded}
    <!-- Setup progress banner -->
    <div class="rounded-lg border border-border bg-muted/40 px-4 py-3 flex items-center gap-3 text-sm">
      <span class="flex items-center gap-1.5 font-medium {!page.data.isApiKeyConfigured ? 'text-foreground' : 'text-muted-foreground line-through'}">
        <span class="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold {!page.data.isApiKeyConfigured ? 'bg-primary text-primary-foreground' : 'bg-green-500 text-white'}">
          {#if page.data.isApiKeyConfigured}✓{:else}1{/if}
        </span>
        Configure AI
      </span>
      <ChevronRight class="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      <span class="flex items-center gap-1.5 {page.data.isApiKeyConfigured ? 'font-medium text-foreground' : 'text-muted-foreground'}">
        <span class="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold {page.data.isApiKeyConfigured ? 'bg-primary text-primary-foreground' : 'bg-muted-foreground/30 text-muted-foreground'}">2</span>
        Setup profile
      </span>
    </div>
  {/if}
```

Note: this inserts the banner as the first child inside the outer `<div class="max-w-2xl space-y-6">` wrapper, using the space-y-6 gap. The outer div's closing tag at line 98 is unchanged.

- [ ] Run type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/routes/settings/+page.svelte && rtk git commit -m "feat: show setup step progress on settings page during onboarding"
```
