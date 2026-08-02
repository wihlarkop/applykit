# Session-expiry Draft Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve supported long-form frontend state through password-session expiry and restore it automatically after sign-in without replaying failed mutations.

**Architecture:** Add a versioned `sessionStorage` engine that stores unarmed working copies, arms all ApplyKit drafts when auth expires, and atomically consumes only valid armed drafts. Each supported route owns a typed adapter that serializes only approved state and restores after profile/route initialization. Auth state distinguishes expiry/401 from manual sign-out.

**Tech Stack:** Svelte 5 runes, TypeScript, Bun test, SvelteKit, browser `sessionStorage`.

## Global Constraints

- Use `sessionStorage`, scoped to the current tab.
- Restore automatically and show `Draft restored after sign-in.`.
- Delete the storage copy immediately after successful restore.
- Do not replay mutations.
- Do not store raw uploaded files, credentials, passwords, loading state, or raw errors.
- Draft TTL is exactly 24 hours.
- No tag or release.

## Tasks

1. Add `frontend/src/lib/draft-recovery.ts` and unit tests for versioning, key isolation, arming, consume-and-delete, malformed payloads, TTL, unrelated storage, and recursive `File`/`Blob` rejection.
2. Integrate expiry/401 arming into `auth-state.svelte.ts`; keep manual sign-out non-recovering in `+layout.svelte`.
3. Add profile-scoped adapters for Profile Setup and Import CV, clearing after successful saves and excluding raw uploads.
4. Add profile-scoped adapters for Cover Letter and Generate CV, including completed analysis and generated previews.
5. Add Smart Apply recovery and clear before successful tracker navigation.
6. Run `bun test`, `bun run check`, `bun run build`, and container smoke CI before merge.
