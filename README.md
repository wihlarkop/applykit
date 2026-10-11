# ApplyKit

![ApplyKit Banner](assets/banner.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-2-orange)](https://kit.svelte.dev)

**Self-hosted, local-first tools for creating tailored resumes, cover letters, and job applications with AI.**

ApplyKit keeps profiles, generated documents, application history, and provider credentials on infrastructure you control. It supports hosted AI providers and local Ollama models without requiring an ApplyKit subscription.

## Highlights

- Multiple role-specific career profiles
- Resume import from PDF, DOCX, or pasted text
- Role-specific resume generation with live preview and PDF export
- Explainable Resume Readiness for PDF parseability, content quality, and supported job tailoring
- Evidence-based Role Evidence Match with separate confidence and eligibility
- Tailored cover letters and guided application preparation
- Application tracking, document history, and AI usage reporting
- Curated and custom AI models across hosted and local providers
- Encrypted multi-credential storage with manual, failover, and round-robin routing
- Optional single-owner password protection for self-hosted deployments
- Guided Profile Ready and AI Ready setup

## Role Evidence Match

Role Evidence Match shows how strongly the evidence in a career profile supports the requirements in a job description. A language model extracts atomic requirements and proposes evidence links, while fixed deterministic rules calculate the score, confidence, and eligibility status.

The result keeps three questions separate:

- **Evidence match** — how strongly the profile supports the role requirements.
- **Confidence** — how complete, reliable, and consistent the available evidence is.
- **Eligibility** — explicit job-related conditions such as work authorization, licensing, required location, or a language genuinely needed for the work.

When the evidence is too incomplete or inconsistent, ApplyKit shows **Analysis needs review** rather than inventing a score. Users can correct requirement priority or evidence links, and each correction creates a new immutable analysis version for audit and comparison. Protected and non-job-related attributes are excluded from scoring.

Role Evidence Match is application guidance. It is **not a hiring probability**, an ATS pass probability, or an automated hiring decision.

See [Role Evidence Match](guides/role-evidence-match.md) for category weights, evidence multipliers, recency rules, score limits, confidence, fairness guardrails, versioned overrides, and the golden evaluation suite.

## Resume Readiness

Resume Readiness validates a saved ApplyKit resume after rendering it to PDF and extracting the PDF text again.

It keeps three document questions separate:

- **ATS Parseability** — whether software can reliably extract essential resume information.
- **Resume Quality** — whether the content is clear, consistent, concise, and evidence-based.
- **Job Tailoring** — whether a job-specific resume surfaces supported profile evidence without adding unsupported keywords.

Fixed rules calculate category and overall results. Critical extraction failures can cap the result or produce **Analysis needs review**. Operational failures have no score rather than being represented as a low-quality resume.

Resume Readiness does **not** claim a probability of passing an employer's ATS. See [Resume Readiness](guides/resume-readiness.md) for categories, score bands, hard gates, limitations, and route compatibility.

## Stable installation with Docker

`main` contains ongoing development. For normal self-hosted use, check out the latest published Git tag.

### Linux, macOS, Git Bash, or WSL

```bash
git clone https://github.com/wihlarkop/applykit.git
cd applykit
git fetch --tags
git checkout "$(git describe --tags --abbrev=0)"
docker compose up --build
```

### Windows PowerShell

```powershell
git clone https://github.com/wihlarkop/applykit.git
cd applykit
git fetch --tags
$tag = git describe --tags --abbrev=0
git checkout $tag
docker compose up --build
```

Open `http://localhost:3000`. The backend is available at `http://localhost:8000`.

A detached `HEAD` is expected when running a stable tag. Docker stores application data and the credential encryption key in separate persistent volumes.

See [Installation](guides/installation.md) for first-run, storage, and manual development instructions.

## Updating an existing installation

Back up both the database and credential encryption key before upgrading.

Docker upgrades run database migrations automatically when the backend starts. Manual installations must run:

```bash
git pull --ff-only
make install
make migrate
```

Then restart the backend and frontend. Existing AI configurations need one successful connection retest after upgrading to establish the trusted readiness fingerprint.

Read [Upgrading](guides/upgrading.md) before changing tags or restoring data.

## Documentation

- [Installation](guides/installation.md) — Docker, manual development, first launch, and storage
- [Upgrading](guides/upgrading.md) — backups, migrations, tag upgrades, and rollback cautions
- [Role Evidence Match](guides/role-evidence-match.md) — evidence-based scoring, confidence, eligibility, fairness, audit history, and limitations
- [Resume Readiness](guides/resume-readiness.md) — PDF parseability, resume quality, supported tailoring, hard gates, and limitations
- [Configuration](guides/configuration.md) — environment variables, local mode, remote mode, and CORS
- [Authentication](guides/authentication.md) — owner setup, sessions, lockout, and password recovery
- [AI providers](guides/ai-providers.md) — models, credentials, routing, Ollama, and readiness
- [Security](guides/security.md) — deployment boundaries, credential encryption, and limitations
- [Backup and restore](guides/backup-and-restore.md) — separate data/key backups and recovery order
- [Changelog](CHANGELOG.md) — release history and upgrade notes

## Development setup

This path follows `main` and is intended for contributors. Requirements: [uv](https://docs.astral.sh/uv/) and [Bun](https://bun.sh/).

```bash
git clone https://github.com/wihlarkop/applykit.git
cd applykit
git switch main
git pull --ff-only
cp backend/.env.example backend/.env
make install
make migrate
```

Start the backend and frontend in separate terminals:

```bash
make backend     # http://localhost:8000
make frontend    # http://localhost:5173
```

The manual backend binds to `127.0.0.1` in local mode.

## Useful commands

```bash
make install
make migrate
make backend
make frontend
make lint

docker compose up --build
docker compose logs -f backend
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run python -m app.cli auth reset-password
```

## Stack

- **Frontend:** SvelteKit 2, Svelte 5, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Python 3.12, SQLAlchemy, Alembic
- **Database:** SQLite by default
- **Authentication:** optional Argon2id owner password and opaque database sessions
- **Credential encryption:** Fernet authenticated encryption
- **AI:** LiteLLM with hosted providers and Ollama support
- **PDF:** WeasyPrint and pdfplumber

## Contributing

Focused pull requests are welcome. Follow existing FastAPI and Svelte patterns, add regression coverage for behavior changes, and keep the local-first design intact.

```bash
bun install
bun x lefthook install
```

## License

MIT — see [LICENSE](LICENSE).
