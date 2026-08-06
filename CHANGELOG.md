# Changelog

All notable changes to ApplyKit are documented here.

The project follows Semantic Versioning. Minor releases add backward-compatible features, while major releases are reserved for breaking changes.

## [1.3.0] - 2026-08-06

### Added

- Evidence-based Role Evidence Match with atomic job requirements, semantic clustering, mention counts, importance conflicts, deterministic category weights, evidence-strength rules, duration handling, technology equivalence, recency modifiers, and bounded corroboration.
- Separate confidence and eligibility results so incomplete evidence and explicit job conditions are not hidden inside one percentage.
- Fairness guardrails that remove protected identity fields from the analysis payload and exclude potentially non-job-related requirements while continuing the remaining analysis.
- Safe failure behavior that displays **Analysis needs review** instead of a guessed score when structured extraction, evidence coverage, confidence, or conflict thresholds are insufficient.
- Immutable analysis snapshots with requirement, evidence, model, rules, prompt, exclusion, failure, and scoring audit data.
- Optional human corrections for requirement priority, experience status, and evidence links, including safe carry-forward states and restoration through new snapshots.
- Human-friendly match results with strengths, concerns, next-step coaching, progressive requirement/evidence disclosure, version comparison, and audit history.
- Deterministic golden evaluation scenarios for keyword stuffing, equivalent tools, recency, experience duration, overlapping roles, incomplete profiles, eligibility ambiguity, protected-field invariance, exclusions, and normalized model variation.

### Changed

- Smart Apply and Cover Letter now use Role Evidence Match while preserving existing page drafts and workflows.
- Cover-letter generation uses a server-verified analysis ID and ignores score or fit context supplied by the browser.
- Cover-letter history and the application tracker distinguish **Evidence match**, **Legacy score**, and records without a score.
- Application score precedence now uses the latest direct authoritative analysis, then a linked cover-letter analysis, then a legacy score.
- Overall scores are displayed in increments of five, including when an essential-requirement limit applies.

### Compatibility

- The legacy `/api/analyze/fit` contract remains available in v1.3.0 with a deprecation warning.
- Existing model-generated scores remain visible as **Legacy AI fit score** and are not recalculated or silently converted.
- Existing cover letters, profiles, application history, and tracker records remain available.
- Role Evidence Match is application guidance and is not a hiring probability, ATS pass probability, or automated selection decision.

### Upgrade notes

- Back up the SQLite database and credential encryption key separately before upgrading.
- Docker installations run Alembic migrations automatically at backend startup.
- Manual installations must run `make install` followed by `make migrate` before starting the backend.
- The migration adds `role_match_analysis`, `role_match_requirement`, `role_match_evidence`, and `role_match_override`, plus a nullable analysis link on generated cover letters.
- Do not replace or delete the credential encryption key. Existing encrypted provider credentials require the original key.
- Run a new analysis to create a Role Evidence Match snapshot; legacy scores are preserved but not recalculated.
- Review any result marked **Analysis needs review** before using its guidance.

## [1.2.0] - 2026-08-04

### Added

- Curated AI provider and model catalog with searchable selection, custom model IDs, provider credential links, and configured integration testing.
- Encrypted multi-credential vault with masked metadata, duplicate detection, per-provider limits, and migration from legacy plaintext settings.
- Manual, automatic failover, and round-robin credential routing with bounded retries, cooldowns, and safe streaming behavior.
- Optional single-owner authentication with Argon2id passwords, opaque sessions, CSRF and Origin protection, login lockout, session revocation, and CLI password reset.
- Browser authentication flows, Security settings, session-expiry warnings, and per-tab draft recovery after reauthentication.
- Guided onboarding with active-profile completeness, fingerprint-verified AI readiness, dashboard guidance, and focused notices on AI-dependent pages.
- Configurable Ollama Base URL and complete provider disconnect behavior.

### Changed

- Redesigned AI integration settings around compact connected-provider views, searchable model browsing, credential management, and responsive accessible editing.
- Hardened local and remote deployment boundaries, CORS validation, error sanitization, prompt boundaries, structured output validation, and scraper SSRF protection.
- Separated Docker application data and credential-key storage, with safe legacy-key migration and container smoke coverage.
- Improved Docker image reliability, frontend production runtime packaging, usage logging, request client reuse, and generation/history durability.
- Clarified that stable installations should use published Git tags while `main` remains the development branch.

### Fixed

- Database schemas that have not been migrated now report clear `make migrate` guidance instead of being misreported as invalid encryption keys.
- Provider settings refresh immediately after saves, and keyless providers such as Ollama remain usable throughout configuration and CV enhancement.
- Corrected usage date filtering and totals, internal error disclosure, connection-test sanitization, and several CV import edge cases.

### Upgrade notes

- Back up the SQLite database and credential encryption key separately before upgrading.
- Docker installations run Alembic migrations automatically at backend startup.
- Manual installations must run `make install` followed by `make migrate` before starting the backend.
- Do not replace or delete the credential encryption key. Existing encrypted provider credentials require the original key.
- Existing AI configurations require one successful connection retest after upgrading so ApplyKit can establish the new readiness fingerprint.

[1.3.0]: https://github.com/wihlarkop/applykit/releases/tag/v1.3.0
[1.2.0]: https://github.com/wihlarkop/applykit/releases/tag/v1.2.0
