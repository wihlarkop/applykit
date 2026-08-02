# ApplyKit

![ApplyKit Banner](assets/banner.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-2-orange)](https://kit.svelte.dev)

**Self-hosted, local-first tools for creating tailored resumes, cover letters, and job applications with AI.**

ApplyKit stores profiles, generated documents, application history, and provider credentials on infrastructure you control. No subscription is required.

> ApplyKit defaults to local mode without login. Keep that mode on localhost. Remote deployments should enable protected mode and use HTTPS, or be placed behind an authentication proxy.

## Highlights

- Multiple role-specific profiles
- Resume import from PDF, DOCX, or pasted text
- ATS-focused resume enhancement and PDF export
- Tailored cover letters with streaming output
- Job URL parsing, fit analysis, and Smart Apply
- Kanban application tracker and generation history
- Token, cost, latency, and error usage reporting
- Curated and custom models across hosted and local providers
- Multiple encrypted credentials per provider
- Manual, automatic failover, and round-robin credential routing
- Optional single-owner password protection

## Quick Start

### Docker

```bash
git clone https://github.com/wihlarkop/applykit.git
cd applykit
docker compose up --build
```

Open `http://localhost:3000`. The backend is available at `http://localhost:8000`, and persistent data is stored in the Docker volume `applykit_applykit-data`.

### Manual development setup

Requirements: [uv](https://docs.astral.sh/uv/) and [Bun](https://bun.sh/).

```bash
git clone https://github.com/wihlarkop/applykit.git
cd applykit
cp backend/.env.example backend/.env
make install
make migrate
```

Start the backend and frontend in separate terminals:

```bash
make backend     # http://localhost:8000
make frontend    # http://localhost:5173
```

## Optional Protected Mode

ApplyKit supports two startup modes:

```env
AUTH_MODE=disabled  # default; localhost only
AUTH_MODE=password  # single-owner protected mode
```

Protected mode secures the whole installation and every career profile with one owner password. It does not create separate accounts for individual profiles.

The backend foundation is available in this release. The matching browser setup and login screens are delivered by the frontend authentication follow-up.

### First owner setup

Run migrations, start ApplyKit with `AUTH_MODE=password`, then read the backend log:

```bash
# Docker
docker compose logs backend

# Manual
cd backend
uv run alembic upgrade head
uv run main.py
```

An unclaimed installation prints a one-time setup token. The token:

- expires after 30 minutes;
- is stored only as a hash;
- is replaced when an unclaimed backend restarts;
- becomes invalid immediately after owner setup.

Owner passwords must contain 12–128 characters. Passphrases are supported without forced uppercase, number, or symbol rules. Passwords are stored as Argon2id PHC hashes.

### Sessions and request protection

- Normal sessions expire 7 days after login.
- **Remember this device** sessions expire after 30 days.
- Expiry is absolute and does not extend with activity.
- Session and CSRF token hashes are stored in SQLite; raw session tokens stay in cookies.
- Session cookies are `HttpOnly` and `SameSite=Lax`.
- Mutating requests require a session-bound CSRF token and an allowed `Origin`.
- Five failed attempts within 10 minutes lock authentication for 15 minutes.
- Logout revokes the current session. Password reset revokes every session.

Only health checks and the required setup/login endpoints remain public. Application data, AI settings, credentials, and API documentation require authentication in protected mode.

### Remote HTTPS deployment

For localhost over HTTP:

```env
COOKIE_SECURE=false
```

For any remote HTTPS deployment:

```env
AUTH_MODE=password
COOKIE_SECURE=true
CORS_ORIGINS=["https://applykit.example.com"]
```

Do not expose protected mode through public plain HTTP. ApplyKit logs a warning when password mode starts with `COOKIE_SECURE=false`.

### Forgotten password

There is no email recovery or recovery key. Reset the password from the machine running ApplyKit:

```bash
# Docker
docker compose exec backend uv run python -m app.cli auth reset-password

# Manual
cd backend
uv run python -m app.cli auth reset-password
```

The reset command asks for the new password twice, clears login lockout, and signs out every active session.

### API documentation

```text
DEBUG=false
→ /docs, /redoc, and /openapi.json are disabled

DEBUG=true + AUTH_MODE=disabled
→ API documentation is public

DEBUG=true + AUTH_MODE=password
→ API documentation requires a valid session
```

## AI Providers and Credentials

Open **AI Settings** from the gear icon to:

- connect and test providers;
- choose a catalog or supported custom model;
- save multiple labeled credentials;
- select an active credential manually;
- enable automatic failover or round robin.

Manual routing is the default. Automatic modes require at least two enabled credentials and allow 2–5 attempts per operation. Streaming requests are never retried after output has started.

Ollama does not require an API key. Some non-AI features remain usable without configuring a provider.

## Credential Security and Backups

Provider secrets are encrypted before being stored. The API and frontend receive masked values only.

Local installations create:

```text
backend/.applykit/credential.key
```

Back up this file together with `backend/applykit.db`. Encrypted credentials cannot be recovered without the same key.

Docker stores both the SQLite database and encryption key in `/data`. Back up the complete volume:

```bash
docker run --rm \
  -v applykit_applykit-data:/data \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/applykit-backup.tar.gz /data
```

For managed deployments, set a persistent Fernet key:

```env
CREDENTIAL_ENCRYPTION_KEY=<persistent-fernet-key>
MAX_PROVIDER_CREDENTIALS=20
```

Never rotate or delete the encryption key without first migrating stored credentials.

## Configuration

Common backend variables in `backend/.env`:

```env
DATABASE_URL=sqlite:///./applykit.db
AUTH_MODE=disabled
COOKIE_SECURE=false
DEBUG=false
CORS_ORIGINS=["http://localhost:5173"]
CREDENTIAL_KEY_FILE=.applykit/credential.key
MAX_PROVIDER_CREDENTIALS=20
```

For a remote frontend build, set the browser-reachable API URL:

```bash
VITE_API_BASE_URL=https://api.example.com/api docker compose up --build
```

## Stack

- **Frontend:** SvelteKit 2, Svelte 5, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Python 3.12, SQLAlchemy, Alembic
- **Database:** SQLite by default
- **Authentication:** optional Argon2id owner password and opaque database sessions
- **AI:** LiteLLM
- **PDF:** WeasyPrint
- **Scraping:** direct ATS APIs, Jina Reader, and Crawl4AI fallback

## Useful Commands

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

## Supported Job Sources

ApplyKit has direct parsing for Greenhouse, Lever, and Ashby. Other accessible job pages use the generic scraping and LLM extraction flow.

## Contributing

Focused pull requests are welcome. Follow the existing FastAPI and Svelte 5 patterns, add tests for behavior changes, and keep the local-first design intact.

```bash
bun install
bun x lefthook install
```

## License

MIT — see [LICENSE](LICENSE).
