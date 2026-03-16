# Navbar Revamp — Design Spec

**Date:** 2026-03-16
**Status:** Approved for implementation

## Overview

Reorganize the top navigation bar to address two problems: too many links (8 after Tracker is added) and flat hierarchy where all items look equally important. The solution is a flat nav with visual group separators and a richer profile switcher that absorbs the Profile and Profiles pages.

---

## Design

### Navbar Structure

```
[ApplyKit]  Dashboard  |  Cover Letter  Generate CV  |  History  Tracker      [Profile ▾]  [🌙]  [⚙️]
```

- **Left**: logo + flat nav links with two thin vertical dividers as group separators
- **Right**: profile switcher (full name) + theme toggle + settings icon
- All links are text-only (no icons)
- Active page link: existing `bg-accent text-accent-foreground font-medium` style, unchanged
- Thin divider element between Dashboard and the Generate group, and between the Generate and Track groups

### Group Logic

| Group | Links | Notes |
|-------|-------|-------|
| Home | Dashboard | standalone, no group |
| Generate | Cover Letter, Generate CV | primary actions |
| Track | History, Tracker | primary outcomes |
| Utilities (right) | Profile switcher, Theme toggle, Settings | not in nav links |

### Profile Switcher Dropdown

Clicking the profile button opens a dropdown:

```
── Switch profile ──────────
  🚀 Work Profile       ← active (highlighted)
  🎓 PhD Applications
────────────────────────────
  ✏️ Edit Profile        → /profile
  👥 Manage Profiles     → /profiles
```

- Profile icon + full label shown on the button (e.g. `🚀 Work Profile ▾`)
- Switch section: lists all profiles, active one highlighted
- Divider between switch section and management links
- "Edit Profile" navigates to `/profile`
- "Manage Profiles" navigates to `/profiles`

### Removed from Top Nav

- `Profile` link (`/profile`) — now accessed via switcher dropdown
- `Profiles` link (`/profiles`) — now accessed via switcher dropdown

### Mobile

ApplyKit is a self-hosted personal desktop tool. v1 handles narrow screens with `overflow-x: auto` on the nav — links scroll horizontally. No hamburger menu needed.

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/routes/+layout.svelte` | Remove Profile + Profiles from `navLinks`; add group dividers to nav markup |
| `frontend/src/lib/components/ProfileSwitcher.svelte` | Add "Edit Profile" + "Manage Profiles" links to the existing dropdown |

---

## Out of Scope

- Hamburger / mobile drawer navigation
- Sidebar navigation
- Dropdown menus for nav groups
- Notification badges on nav items
- Breadcrumb navigation
