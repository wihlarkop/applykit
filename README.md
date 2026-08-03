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
- ATS-focused CV enhancement with live preview and PDF export
- Tailored cover letters and Smart Apply workflows
- Application tracker, history, and AI usage reporting
- Curated and custom AI models across hosted and local providers
- Encrypted multi-credential storage with manual, failover, and round-robin routing
- Optional single-owner password protection for self-hosted deployments
- Guided Profile Ready and AI Ready setup

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
- **PDF:** WeasyPrint

## Contributing

Focused pull requests are welcome. Follow existing FastAPI and Svelte patterns, add regression coverage for behavior changes, and keep the local-first design intact.

```bash
bun install
bun x lefthook install
```

## License

MIT — see [LICENSE](LICENSE).
