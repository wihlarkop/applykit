# Changelog

All notable changes to ApplyKit are documented here.

The project follows Semantic Versioning. Minor releases add backward-compatible features, while major releases are reserved for breaking changes.

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

[1.2.0]: https://github.com/wihlarkop/applykit/releases/tag/v1.2.0
