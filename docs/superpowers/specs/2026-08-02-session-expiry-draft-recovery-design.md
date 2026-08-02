# Session-expiry Draft Recovery Design

## Summary

ApplyKit preserves in-progress long-form work when a password-protected Community session expires. Drafts are stored only in the current browser tab through `sessionStorage`, restored automatically after sign-in, announced with `Draft restored after sign-in.`, and removed immediately after a successful restore. Failed requests or mutations are never replayed.

## Scope

Recovery covers Profile Setup, Cover Letter, Generate CV, Smart Apply, and Import CV pasted text plus completed extraction preview. Raw uploaded files, file bytes, passwords, API credentials, request errors, loading flags, and in-flight request state are never stored.

## Storage and lifecycle

Drafts use a versioned envelope with `version`, `savedAt`, `armed`, and typed `data`. Keys use `applykit:draft:v1:` plus route and active profile ID. Entries expire after exactly 24 hours.

Working copies remain unarmed during ordinary navigation. Session expiry or a `401` arms all ApplyKit drafts in the current tab before auth state is cleared. After login, the original route consumes its matching armed draft, validates it, applies it, removes the storage copy, and displays the restore notification. Manual sign-out does not arm drafts.

## Payloads

- Profile: full `ProfileData` and active editor tab.
- Cover Letter: job inputs and metadata, tone/context, completed fit analysis, interview-prep visibility, and generated or partially streamed letter text.
- Generate CV: job description, completed generated preview, and enhanced flag.
- Smart Apply: job input, completed scrape/fit results, editable metadata, and document generation configuration.
- Import CV: tab, pasted text, and completed extraction preview only. `File` and `Blob` values are recursively rejected.

## Cleanup

Profile and Import drafts clear after successful saves. Smart Apply clears before successful tracker navigation. Consumed, malformed, unsupported, future-dated, and expired entries are removed. Storage failures never interrupt editing or auth handling.

## Testing

Unit tests cover key construction, profile isolation, versioned save, arming, unrelated storage, atomic consume-and-delete, malformed/version/TTL cleanup, and recursive binary rejection. Frontend verification requires `bun test`, `bun run check`, `bun run build`, and green container smoke CI.

## Non-goals

Cross-tab/device recovery, backend storage, automatic request replay, raw upload recovery, OAuth, and multi-user behavior are excluded.
