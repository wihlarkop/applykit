# ApplyKit

![ApplyKit Banner](assets/banner.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-2-orange)](https://kit.svelte.dev)

**Self-hosted, local-first tools for creating tailored CVs, cover letters, and job applications with AI.**

ApplyKit stores profiles, generated documents, application history, and provider credentials on infrastructure you control. No account or subscription is required.

> **Self-hosted only.** ApplyKit has no built-in authentication. Keep it on localhost or protect remote deployments with an authentication proxy such as Cloudflare Access, Authelia, or Nginx basic auth.

## Highlights

- Multiple role-specific profiles
- CV import from PDF, DOCX, or pasted text
- ATS-focused CV enhancement and PDF export
- Tailored cover letters with streaming output
- Job URL parsing, fit analysis, and Smart Apply
- Kanban application tracker and generation history
- Token, cost, latency, and error usage reporting
- Curated models for Gemini, OpenAI, Anthropic, DeepSeek, Groq, Mistral, Hugging Face, OpenRouter, xAI, and Ollama
- Multiple encrypted credentials per provider
- Manual selection, automatic failover, and round-robin credential routing

## Quick Start

### Docker

```bash
git clone https://github.com/wihlarkop/applykit.git
cd applykit
docker compose up --build
```

Open `http://localhost:3000`.

The backend is available at `http://localhost:8000`, and persistent data is stored in the Docker volume `applykit_applykit-data`.

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

## AI Providers and Credentials

Open **AI Settings** from the gear icon to:

- connect and test providers;
- choose a catalog or supported custom model;
- save multiple labeled credentials such as Personal, Work, and Backup;
- choose the active credential manually;
- enable **Automatic failover** for conservative retries;
- enable **Round robin** to distribute requests across healthy credentials.

Manual routing is the default. Automatic modes require at least two enabled credentials and allow 2–5 attempts per operation. Streaming requests are never retried after output has started.

Ollama does not require an API key. Some non-AI features also remain usable without configuring a provider.

## Credential Security and Backups

Provider secrets are encrypted before being stored in the database. The API and frontend only receive masked values.

For local installations, ApplyKit creates:

```text
backend/.applykit/credential.key
```

Back up this file together with `backend/applykit.db`. Encrypted credentials cannot be recovered without the same key.

Docker stores both the SQLite database and encryption key in `/data`, so back up the complete volume:

```bash
docker run --rm \
  -v applykit_applykit-data:/data \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/applykit-backup.tar.gz /data
```

For managed deployments, set a persistent Fernet key instead of relying on a generated file:

```env
CREDENTIAL_ENCRYPTION_KEY=<persistent-fernet-key>
MAX_PROVIDER_CREDENTIALS=20
```

Never rotate or delete the encryption key without first migrating the stored credentials.

## Configuration

Common backend variables in `backend/.env`:

```env
DATABASE_URL=sqlite:///./applykit.db
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
