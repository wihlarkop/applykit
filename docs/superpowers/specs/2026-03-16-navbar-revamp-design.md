# Navbar Revamp — Design Spec

**Date:** 2026-03-16
**Status:** Approved for implementation

## Overview

Reorganize the top navigation bar to address two problems: too many links (8 after Tracker is added) and flat hierarchy where all items look equally important. The solution is a flat nav with visual group separators and a richer profile switcher that absorbs the Profile and Profiles pages.

---

## Design

### Navbar Structure

```
[ApplyKit]  Dashboard  |  Cover Letter  Generate CV  |  History  Tracker      [● 🚀 Work Profile ▼]  [🌙]  [⚙️]
```

Left-to-right order (exact):
1. `ApplyKit` logo link
2. `Dashboard`
3. Divider
4. `Cover Letter`
5. `Generate CV`
6. Divider
7. `History`
8. `Tracker`
9. Flex spacer
10. `ProfileSwitcher` (full label already shown — no change to button markup)
11. `ThemeToggle`
12. `SettingsButton`

- All nav links are text-only (no icons)
- Active page link: `bg-accent text-accent-foreground font-medium` (existing style, unchanged)
- Dividers are rendered as `<span class="w-px h-4 bg-border mx-2 shrink-0"></span>` between groups

### Implementing Dividers

The `navLinks` array cannot represent dividers as plain objects. Replace the `{#each navLinks}` loop with explicit markup:

```svelte
<nav>
  <a href="/">Dashboard</a>
  <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
  <a href="/cover-letter">Cover Letter</a>
  <a href="/generate">Generate CV</a>
  <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
  <a href="/history">History</a>
  <a href="/tracker">Tracker</a>
</nav>
```

The `navLinks` array is removed entirely. Active state is checked per link using `$page.url.pathname`.

### Profile Switcher Dropdown — Changes

The existing `ProfileSwitcher.svelte` dropdown currently has:
- List of profiles (clicking active profile opens `ProfileModal` in edit mode; clicking others switches)
- "New Profile" button (opens `ProfileModal` in create mode)

**Change:** Replace the "New Profile" button with a "Manage Profiles" link that navigates to `/profiles`.

The modal-based edit behavior is preserved — clicking the active profile still calls `openEdit()` and opens `ProfileModal`. No navigation to `/profile` is added.

Final dropdown structure:
```
● 🚀 Work Profile   active
● 🎓 PhD Applications
─────────────────────
👥 Manage Profiles    → goto('/profiles')
```

"Manage Profiles" navigates to `/profiles` using SvelteKit's `goto()`. Add `import { goto } from '$app/navigation';` at the top of the script block.

Since "New Profile" is removed, also delete the `openCreate` function, the `modalMode === 'create'` template branch, and the `'create'` value from the `modalMode` state type — they become dead code.

### Removed from Top Nav

- `Profile` link (`/profile`) — profile editing remains accessible via clicking the active profile in the switcher (existing modal behavior)
- `Profiles` link (`/profiles`) — now accessible via "Manage Profiles" in the switcher dropdown

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/routes/+layout.svelte` | Remove `navLinks` array; replace `{#each}` loop with explicit nav markup including divider spans; remove Profile and Profiles links |
| `frontend/src/lib/components/ProfileSwitcher.svelte` | Replace "New Profile" button with "Manage Profiles" link using `goto('/profiles')` |

---

## Out of Scope

- Hamburger / mobile drawer navigation (v1: nav scrolls horizontally on narrow screens)
- Sidebar navigation
- Dropdown menus for nav groups
- Notification badges on nav items
- Breadcrumb navigation
- Changing the profile button's visual appearance (already shows color dot + icon + label)
