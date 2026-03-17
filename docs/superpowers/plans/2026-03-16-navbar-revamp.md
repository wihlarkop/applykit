# Navbar Revamp Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat `navLinks` array with explicit grouped nav markup and update the profile switcher to remove "New Profile" in favour of "Manage Profiles."

**Architecture:** Two file changes only. `+layout.svelte` gets explicit nav markup with group dividers. `ProfileSwitcher.svelte` loses `openCreate` and gains a `goto('/profiles')` link.

**Tech Stack:** SvelteKit (Svelte 5 runes), Tailwind CSS 4

---

## Chunk 1: Both File Changes

### Task 1: Update `+layout.svelte`

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: Replace the file content**

Replace the entire file with:

```svelte
<script lang="ts">
  import { page } from '$app/stores';
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import SettingsButton from '$lib/components/SettingsButton.svelte';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';
  import Toaster from '$lib/components/Toaster.svelte';
  import { themeState } from '$lib/theme.svelte';
  import '../app.css';

  let { data, children } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  function navClass(href: string) {
    return `px-3 py-1.5 rounded-md text-sm transition-colors ${
      $page.url.pathname === href
        ? 'bg-accent text-accent-foreground font-medium'
        : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
    }`;
  }

  // Dark mode effect
  $effect(() => {
    if (typeof document !== 'undefined') {
      const isDark = themeState.current === 'dark';
      document.documentElement.classList.toggle('dark', isDark);
      localStorage.setItem('theme', themeState.current);
    }
  });
</script>

<div class="min-h-screen flex flex-col bg-muted/40">
  <header class="sticky top-0 z-60 border-b bg-card">
    <div class="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-4 min-w-0">
        <a
          href={isOnboarded ? '/' : '/onboarding'}
          class="font-bold text-lg tracking-tight hover:text-primary transition-colors shrink-0"
        >ApplyKit</a>

        {#if isOnboarded}
          <nav class="flex items-center gap-1 animate-in fade-in slide-in-from-left-2 duration-500 overflow-x-auto">
            <a href="/" class={navClass('/')}>Dashboard</a>
            <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
            <a href="/cover-letter" class={navClass('/cover-letter')}>Cover Letter</a>
            <a href="/generate" class={navClass('/generate')}>Generate CV</a>
            <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
            <a href="/history" class={navClass('/history')}>History</a>
            <a href="/tracker" class={navClass('/tracker')}>Tracker</a>
          </nav>
        {/if}
      </div>

      {#if isOnboarded}
        <div class="flex items-center gap-3 animate-in fade-in duration-500 shrink-0">
          <ProfileSwitcher />
          <ThemeToggle />
          <SettingsButton />
        </div>
      {/if}
    </div>
  </header>

  <main class="flex-1 mx-auto w-full max-w-5xl px-4 py-8">
    {@render children()}
  </main>

  <Toaster />
</div>
```

Key changes from original:
- `navLinks` array removed
- `{#each}` loop replaced with explicit `<a>` tags + `<span>` dividers
- `Profile` and `Profiles` links removed
- `Cover Letter` now precedes `Generate CV`
- `Tracker` added
- `navClass()` helper function replaces inline ternary in the loop
- `overflow-x-auto` on `<nav>` for narrow screens
- `shrink-0` on logo and right-side controls to prevent them from squishing

- [ ] **Step 2: Verify visually**

Start the frontend:
```bash
cd frontend && bun dev
```

Open `http://localhost:5173`. Check:
- Navbar shows: `ApplyKit  Dashboard | Cover Letter  Generate CV | History  Tracker  [Profile ▾] [🌙] [⚙️]`
- Two thin vertical dividers visible between groups
- Active page link highlighted when navigating between pages
- `/profile` and `/profiles` no longer in the navbar

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/routes/+layout.svelte
rtk git commit -m "feat: navbar revamp — grouped links with dividers, remove Profile/Profiles nav items"
```

---

### Task 2: Update `ProfileSwitcher.svelte`

**Files:**
- Modify: `frontend/src/lib/components/ProfileSwitcher.svelte`

- [ ] **Step 1: Replace the file content**

Replace the entire file with:

```svelte
<script lang="ts">
  import { goto } from '$app/navigation';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { getProfile } from '$lib/api';
  import { profiles } from '$lib/profiles.svelte';
  import ProfileModal from './ProfileModal.svelte';

  let dropdownOpen = $state(false);
  let modalMode = $state<'edit' | null>(null);

  const ap = $derived(activeProfile.current);
  const allProfiles = $derived(profiles.all);

  function switchProfile(p: { id: number; label: string; color: string; icon: string; name: string }) {
    activeProfile.set(p);
    dropdownOpen = false;
  }

  function openEdit() {
    dropdownOpen = false;
    modalMode = 'edit';
  }

  function closeModal() {
    modalMode = null;
  }

  function handleManageProfiles() {
    dropdownOpen = false;
    goto('/profiles');
  }
</script>

<div class="relative">
  <!-- Trigger button -->
  <button
    onclick={() => (dropdownOpen = !dropdownOpen)}
    class="flex items-center gap-2 border rounded-lg px-3 py-2 text-sm font-medium bg-background shadow-sm hover:bg-accent transition-colors min-w-40 justify-between"
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
    <div class="fixed inset-0 z-10" onclick={() => (dropdownOpen = false)}></div>

    <div class="absolute top-full mt-1 left-0 z-20 bg-card border rounded-lg shadow-lg py-1 min-w-[200px]">
      {#each allProfiles as p}
        <button
          onclick={() => (p.id === ap?.id ? openEdit() : switchProfile(p))}
          class="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
        >
          <span class="w-2 h-2 rounded-full shrink-0" style="background:{p.color}"></span>
          <span>{p.icon}</span>
          <span class="truncate flex-1">{p.label}</span>
          {#if !p.has_content}
            <span class="w-1.5 h-1.5 rounded-full bg-yellow-400 shrink-0" title="Profile is empty"></span>
          {/if}
          {#if p.id === ap?.id}
            <span class="text-xs text-muted-foreground">active</span>
          {/if}
        </button>
      {/each}

      <div class="border-t my-1"></div>
      <button
        onclick={handleManageProfiles}
        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
      >
        <span class="text-base">👥</span> Manage Profiles
      </button>
    </div>
  {/if}
</div>

<!-- Edit modal -->
{#if modalMode === 'edit' && ap}
  {#await getProfile(ap.id) then profileData}
    <ProfileModal mode="edit" profile={profileData} onclose={closeModal} />
  {:catch}
    {closeModal()}
  {/await}
{/if}
```

Key changes from original:
- `import { goto } from '$app/navigation'` added
- `modalMode` type narrowed from `'create' | 'edit' | null` to `'edit' | null`
- `openCreate()` function removed
- "New Profile" button replaced with "Manage Profiles" button calling `handleManageProfiles()`
- `{#if modalMode === 'create'}` template branch removed

- [ ] **Step 2: Verify visually**

With the dev server still running, open the profile switcher:
- Dropdown shows all profiles + "Manage Profiles" at the bottom (no "New Profile")
- Clicking a non-active profile switches it
- Clicking the active profile opens the edit modal (unchanged)
- Clicking "Manage Profiles" navigates to `/profiles`

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/lib/components/ProfileSwitcher.svelte
rtk git commit -m "feat: profile switcher — replace New Profile with Manage Profiles link"
```

---

### Task 3: Push

- [ ] **Step 1: Push**

```bash
rtk git push
```
