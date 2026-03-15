# Navbar Redesign + Settings Page Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the active ProfileSwitcher into the persistent navbar, replace the verbose Gemini status text with a gear icon linking to a new read-only `/settings` page.

**Architecture:** `SettingsButton.svelte` is a self-contained navbar icon that fetches `/api/status` on mount and overlays a colored dot only when something is wrong. `ProfileSwitcher` moves from per-page sticky headers into the global navbar. The `/settings` page calls `GET /api/status` and renders provider + connection info read-only with `.env` edit instructions.

**Tech Stack:** SvelteKit 2, Svelte 5 runes, Tailwind CSS v4, lucide-svelte (`@lucide/svelte`), existing `getStatus()` API function.

---

## Chunk 1: SettingsButton component + layout wiring

### Task 1: Create SettingsButton.svelte

**Files:**
- Create: `frontend/src/lib/components/SettingsButton.svelte`

Context: The current `StatusIndicator.svelte` shows verbose text ("gemini/gemini-2.5-flash-lite connected"). We replace it with a gear icon that links to `/settings`. A small colored dot overlays the icon only when status is unhealthy. No dot = silent success.

Status dot rules:
- `error === true` → red dot (`bg-red-500`) — backend unreachable
- `status === null` → no dot — still loading, don't alarm
- `status.api_key_configured === false` → yellow dot (`bg-yellow-500`)
- `status.api_key_configured === true` → no dot

`StatusResponse` is in `$lib/types` and is `{ api_key_configured: boolean; provider: string | null }`.
`getStatus()` is in `$lib/api` and returns `Promise<StatusResponse>`.

Note: Complete Task 1 fully before starting Task 2 — Task 2 imports this file.

- [ ] Create `frontend/src/lib/components/SettingsButton.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { Settings } from '@lucide/svelte';
  import { getStatus } from '$lib/api';
  import type { StatusResponse } from '$lib/types';

  let status: StatusResponse | null = $state(null);
  let error = $state(false);

  onMount(async () => {
    try {
      status = await getStatus();
    } catch {
      error = true;
    }
  });

  const dotColor = $derived(
    error ? 'bg-red-500' :
    status && !status.api_key_configured ? 'bg-yellow-500' :
    null
  );
</script>

<a
  href="/settings"
  class="relative flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
  title="Settings"
>
  <Settings class="w-4 h-4" />
  {#if dotColor}
    <span class="absolute top-0.5 right-0.5 w-2 h-2 rounded-full {dotColor} ring-1 ring-background"></span>
  {/if}
</a>
```

---

### Task 2: Update +layout.svelte — navbar right side

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`

Context: The current layout imports `StatusIndicator` and renders it in the navbar right side. We remove it and add `ProfileSwitcher` + `SettingsButton`.

Current `<script>` imports (relevant lines):
```typescript
import StatusIndicator from '$lib/components/StatusIndicator.svelte';
```

Current navbar right block (the entire `{#if isOnboarded}` block on the right side):
```svelte
{#if isOnboarded}
  <div class="flex items-center gap-3 animate-in fade-in duration-500">
    <ThemeToggle />
    <StatusIndicator />
  </div>
{/if}
```

- [ ] Open `frontend/src/routes/+layout.svelte`.

- [ ] Replace the `StatusIndicator` import with two new imports:
```typescript
// Remove:
import StatusIndicator from '$lib/components/StatusIndicator.svelte';
// Add:
import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
import SettingsButton from '$lib/components/SettingsButton.svelte';
```
`ThemeToggle` is already imported — do not touch it.

- [ ] Replace the navbar right block:
```svelte
{#if isOnboarded}
  <div class="flex items-center gap-3 animate-in fade-in duration-500">
    <ThemeToggle />
    <StatusIndicator />
  </div>
{/if}
```
with:
```svelte
{#if isOnboarded}
  <div class="flex items-center gap-3 animate-in fade-in duration-500">
    <ProfileSwitcher />
    <ThemeToggle />
    <SettingsButton />
  </div>
{/if}
```

- [ ] Run type-check:
```bash
cd frontend && bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/lib/components/SettingsButton.svelte src/routes/+layout.svelte
rtk git commit -m "feat: move ProfileSwitcher to navbar, replace status text with settings gear icon"
```

---

## Chunk 2: Settings page

### Task 3: Create /settings page

**Files:**
- Create: `frontend/src/routes/settings/+page.svelte`

Context: Read-only page. Fetches `GET /api/status` on mount (same `getStatus()` call). Shows provider string and connection status with a colored dot + label. Includes a note with exact env var names explaining how to change config. No forms, no mutations.

States to handle:
- Loading (`status === null && !error`): show pulsing dot + "Checking connection…"
- Error (`error === true`): red dot + "Backend unreachable" message
- Not configured (`status.api_key_configured === false`): yellow dot + "API key not configured"
- Connected (`status.api_key_configured === true`): green dot + "Connected" + provider code block

- [ ] Create the directory `frontend/src/routes/settings/` and file `+page.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { getStatus } from '$lib/api';
  import type { StatusResponse } from '$lib/types';
  import { Settings, Cpu, Info } from '@lucide/svelte';

  let status: StatusResponse | null = $state(null);
  let error = $state(false);

  onMount(async () => {
    try {
      status = await getStatus();
    } catch {
      error = true;
    }
  });
</script>

<div class="max-w-2xl space-y-8">
  <div>
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <Settings class="w-6 h-6 text-primary" />
      Settings
    </h1>
    <p class="text-sm text-muted-foreground mt-1">Application configuration — read only.</p>
  </div>

  <!-- AI Model -->
  <div class="border rounded-xl p-6 bg-card space-y-4">
    <h2 class="font-semibold flex items-center gap-2 text-base">
      <Cpu class="w-4 h-4 text-primary" />
      AI Model
    </h2>

    {#if error}
      <div class="flex items-center gap-2 text-sm text-destructive">
        <span class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>
        Backend unreachable — make sure the server is running.
      </div>
    {:else if status === null}
      <div class="flex items-center gap-2 text-sm text-muted-foreground">
        <span class="w-2 h-2 rounded-full bg-muted animate-pulse shrink-0"></span>
        Checking connection…
      </div>
    {:else if status.api_key_configured}
      <div class="space-y-3">
        <div class="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <span class="w-2 h-2 rounded-full bg-green-500 shrink-0"></span>
          Connected
        </div>
        <div class="text-sm">
          <span class="text-muted-foreground">Provider / Model:</span>
          <code class="ml-2 px-2 py-0.5 rounded bg-muted text-foreground text-xs font-mono">{status.provider}</code>
        </div>
      </div>
    {:else}
      <div class="flex items-center gap-2 text-sm text-yellow-600 dark:text-yellow-400">
        <span class="w-2 h-2 rounded-full bg-yellow-500 shrink-0"></span>
        API key not configured
      </div>
    {/if}

    <div class="pt-2 border-t text-sm text-muted-foreground space-y-1.5">
      <p class="flex items-start gap-1.5">
        <Info class="w-3.5 h-3.5 shrink-0 mt-0.5" />
        To change the model or API key, edit
        <code class="px-1 py-0.5 rounded bg-muted text-xs font-mono">LLM_PROVIDER</code> and
        <code class="px-1 py-0.5 rounded bg-muted text-xs font-mono">LLM_API_KEY</code>
        in your <code class="px-1 py-0.5 rounded bg-muted text-xs font-mono">.env</code> file, then restart the backend.
      </p>
      <p class="pl-5 text-xs">
        Example: <code class="px-1 py-0.5 rounded bg-muted font-mono">LLM_PROVIDER=gemini/gemini-2.5-flash-lite</code>
      </p>
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
rtk git add src/routes/settings/+page.svelte
rtk git commit -m "feat: add /settings page with read-only LLM status"
```

---

## Chunk 3: Remove per-page ProfileSwitchers

### Task 4: Clean up profile/+page.svelte

**Files:**
- Modify: `frontend/src/routes/profile/+page.svelte`

Context: In a previous session, `ProfileSwitcher` was embedded in the sticky header of this page. Now that it lives in the global navbar, remove it from the page and restore the clean title structure.

Current header left side in `frontend/src/routes/profile/+page.svelte`:
```svelte
<div class="flex items-center gap-3">
  <ProfileSwitcher />
  <div>
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <User class="w-6 h-6 text-primary" />
      Profile Setup
    </h1>
    <p class="text-xs text-muted-foreground mt-0.5 font-medium uppercase tracking-wider">Secure your professional baseline.</p>
  </div>
</div>
```

- [ ] Replace that block with:
```svelte
<div>
  <h1 class="text-2xl font-bold flex items-center gap-2">
    <User class="w-6 h-6 text-primary" />
    Profile Setup
  </h1>
  <p class="text-xs text-muted-foreground mt-0.5 font-medium uppercase tracking-wider">Secure your professional baseline.</p>
</div>
```

- [ ] Remove from the `<script>` block (ProfileSwitcher is only used in the one header location we just replaced — removing the import is safe):
```typescript
import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
```

---

### Task 5: Clean up generate/+page.svelte

**Files:**
- Modify: `frontend/src/routes/generate/+page.svelte`

Current header left side in `frontend/src/routes/generate/+page.svelte`:
```svelte
<div class="flex items-center gap-3">
  <ProfileSwitcher />
  <div>
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <Sparkles class="w-6 h-6 text-primary" />
      Generate CV
    </h1>
    <p class="text-xs text-muted-foreground mt-0.5">Create an ATS-optimized CV tailored from your profile.</p>
  </div>
</div>
```

- [ ] Replace that block with:
```svelte
<div>
  <h1 class="text-2xl font-bold flex items-center gap-2">
    <Sparkles class="w-6 h-6 text-primary" />
    Generate CV
  </h1>
  <p class="text-xs text-muted-foreground mt-0.5">Create an ATS-optimized CV tailored from your profile.</p>
</div>
```

- [ ] Remove from the `<script>` block:
```typescript
import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
```

---

### Task 6: Clean up cover-letter/+page.svelte

**Files:**
- Modify: `frontend/src/routes/cover-letter/+page.svelte`

Current header left side in `frontend/src/routes/cover-letter/+page.svelte`:
```svelte
<div class="flex items-center gap-3">
  <ProfileSwitcher />
  <div>
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <Mail class="w-6 h-6 text-primary" />
      Cover Letter Generator
    </h1>
    <p class="text-xs text-muted-foreground mt-0.5">Write a perfectly tailored cover letter instantly based on a job description.</p>
  </div>
</div>
```

- [ ] Replace that block with:
```svelte
<div>
  <h1 class="text-2xl font-bold flex items-center gap-2">
    <Mail class="w-6 h-6 text-primary" />
    Cover Letter Generator
  </h1>
  <p class="text-xs text-muted-foreground mt-0.5">Write a perfectly tailored cover letter instantly based on a job description.</p>
</div>
```

- [ ] Remove from the `<script>` block:
```typescript
import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
```

- [ ] Run final type-check:
```bash
bun run check
```
Expected: 0 errors.

- [ ] Commit:
```bash
rtk git add src/routes/profile/+page.svelte src/routes/generate/+page.svelte src/routes/cover-letter/+page.svelte
rtk git commit -m "chore: remove per-page ProfileSwitcher now that it lives in navbar"
```

---

## Summary

After all tasks:
1. Navbar right side: `[ProfileSwitcher pill] [🌙] [⚙️]` — always visible when onboarded
2. Gear icon shows a red/yellow dot only when AI config is broken; silent otherwise
3. `/settings` shows current provider string + connection status + `.env` edit instructions
4. Profile, Generate, Cover Letter page headers are clean — no switcher duplication
