# ApplyKit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Self-hosted, local-first CV and cover letter generator powered by AI. Your data stays on your machine — no cloud, no account, no subscription.

---

## Features

- **Multi-profile support** — create separate profiles for different roles (e.g. "Software Engineer", "Product Manager"), each with its own history and color
- **AI CV generation** — rewrites bullet points and summary to be ATS-optimized for a specific job description
- **AI cover letter generation** — writes a tailored cover letter from your profile + job description in seconds
- **CV import** — paste or upload an existing PDF/DOCX and AI extracts your profile automatically
- **History** — every generated CV and cover letter is saved and browsable, filterable by profile
- **PDF export** — download as PDF or use browser print
- **LLM-agnostic** — works with Gemini, OpenAI, Anthropic, Mistral, or any local model via Ollama
- **Works without an API key** — CV generation falls back to your raw profile data if no LLM is configured

---

## How It Works

```
Browser (localhost:5173)
       │
       ▼
  SvelteKit Frontend
  - Profile editor (multi-profile)
  - CV preview & export
  - Cover letter editor
  - History browser
       │  HTTP (REST API)
       ▼
  FastAPI Backend (localhost:8000)
  - Profile CRUD (SQLite, multi-profile)
  - CV import (PDF/DOCX/text → LLM extraction)
  - ATS CV enhancement (LLM)
  - Cover letter generation (LLM)
  - PDF export (WeasyPrint)
  - Generation history
       │
       ▼
  LiteLLM → any LLM provider (Gemini, OpenAI, Anthropic, Ollama...)
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | SvelteKit 2 + Svelte 5 (runes) + TypeScript |
| Styling | Tailwind CSS v4 + shadcn-svelte |
| Backend | FastAPI + Python 3.12 |
| Database | SQLite via SQLAlchemy 2.0 + Alembic |
| AI | LiteLLM (default: `gemini/gemini-1.5-flash`) |
| PDF | WeasyPrint (server-side) + browser print (client-side) |
| CV parsing | pdfplumber (PDF), python-docx (DOCX) |
| Package managers | uv (Python), Bun (JavaScript) |

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager (`pip install uv` or see docs)
- [Bun](https://bun.sh/) — JavaScript runtime (`curl -fsSL https://bun.sh/install | bash`)
- An LLM API key — free options:
  - [Google AI Studio](https://aistudio.google.com/) for Gemini (recommended, generous free tier)
  - [OpenAI](https://platform.openai.com/), [Anthropic](https://console.anthropic.com/), or any [LiteLLM-supported provider](https://docs.litellm.ai/docs/providers)
  - Or [Ollama](https://ollama.com/) for fully local, offline usage

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd applykit
```

### 2. Configure the backend

```bash
cd backend

# Copy environment template
cp .env.example .env

# Edit .env and set your LLM credentials (see Environment Variables section)
```

### 3. Install backend dependencies

```bash
uv sync
```

### 4. Run database migrations

```bash
uv run alembic upgrade head
```

### 5. Start the backend

```bash
uv run main.py
# Runs at http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

### 6. Install and start the frontend

```bash
cd ../frontend
bun install
bun run dev
# Runs at http://localhost:5173
```

Open `http://localhost:5173` — you should see the dashboard.

---

## Environment Variables

All variables go in `backend/.env`. They are never committed or sent to the browser.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini/gemini-1.5-flash` | LiteLLM model string |
| `LLM_API_KEY` | *(required for AI features)* | API key for the chosen provider |
| `DATABASE_URL` | `sqlite:///./applykit.db` | SQLite database path |

### Provider examples

```env
# Google Gemini (free tier available)
LLM_PROVIDER=gemini/gemini-1.5-flash
LLM_API_KEY=AIza...

# OpenAI
LLM_PROVIDER=gpt-4o-mini
LLM_API_KEY=sk-...

# Anthropic
LLM_PROVIDER=claude-haiku-4-5-20251001
LLM_API_KEY=sk-ant-...

# Local Ollama (no API key needed, runs fully offline)
LLM_PROVIDER=ollama/llama3.2
LLM_API_KEY=ollama
```

> **No API key?** The app still works. CV generation falls back to your raw profile data without AI enhancement. Import and cover letter generation require an API key.

---

## Quick Start (Makefile)

A `Makefile` is included for common tasks:

```bash
make install     # Install all dependencies (backend + frontend)
make migrate     # Run database migrations
make backend     # Start backend server (http://localhost:8000)
make frontend    # Start frontend dev server (http://localhost:5173)
make lint        # Lint frontend TypeScript/Svelte
make migrate-new MSG="add column"  # Create a new migration
make migrate-down                  # Roll back the last migration
make help        # Show all available commands
```

> **Full setup in 4 commands:**
> ```bash
> cp backend/.env.example backend/.env  # then edit with your API key
> make install
> make migrate
> # then in two terminals:
> make backend
> make frontend
> ```

---

## Usage

### 1. Create a profile

On first launch you'll be prompted to set up your profile. Fill in:
- Personal info (name, email, location, LinkedIn, GitHub)
- Work experience with bullet points
- Education
- Skills
- Projects and certifications

Or use **AI Sync** (the sparkle button at the top of the profile page) to upload an existing CV and auto-fill everything instantly.

### 2. Multi-profile setup (optional)

ApplyKit supports multiple profiles — useful if you're applying for roles in different fields or want different versions of your CV.

- Click the profile switcher in the top navigation bar to create a new profile
- Each profile has its own label, color, icon, and content
- History is stored per-profile and can be filtered by profile

### 3. Generate a CV

1. Go to **Generate CV** (or press the button on the dashboard)
2. Optionally paste a job description — the AI will tailor bullet points to match its keywords
3. Click **Generate ATS CV**
4. Preview the result, then **Download PDF** or **Print**

Generated CVs are saved to history automatically.

### 4. Write a cover letter

1. Go to **Cover Letter**
2. Fill in the company name (optional), job description, and any emphasis notes
3. Click **Write Cover Letter**
4. Copy the text, download as PDF, or print

Generated letters are saved to history automatically.

### 5. Import an existing CV

1. Go to **Import CV** (or use AI Sync from the profile page)
2. Upload a PDF/DOCX file, or paste the text directly
3. The AI extracts all fields and populates your profile
4. Review and save

### 6. Browse history

Go to **History** to see every generated CV and cover letter. Filter by profile using the pill buttons at the top. Click any entry to preview it, regenerate from it, copy, or delete.

---

## Roadmap

Items marked ✅ are already shipped. Everything else is planned or in consideration.

### UX Polish
| Status | Feature | Description |
|--------|---------|-------------|
| ✅ | Animated toast notifications | Floating feedback for every action |
| ✅ | Skeleton screen loading | Shimmer placeholders during AI generation |
| ✅ | Profile scrollspy navigation | Sticky sidebar with section highlighting |
| ✅ | Confetti on first CV generation | Moment of delight after generating |
| ✅ | Multi-profile support | Separate identities for different target roles |
| ✅ | Generation history | Browse, preview, and delete past CVs and letters |
| ⬜ | Real-time CV preview | Split-screen editor with live-updating preview |
| ⬜ | Dark mode | Deep Night theme with high-contrast accessibility variants |

### AI Features
| Status | Feature | Description |
|--------|---------|-------------|
| ✅ | ATS CV enhancement | AI rewrites bullet points and summary for a target job description |
| ✅ | Cover letter generation | Tailored cover letter from profile + job description |
| ✅ | CV import (PDF/DOCX) | AI extracts profile fields from an uploaded file |
| ⬜ | AI skill gap analysis | Compare profile against a JD and highlight missing keywords |
| ⬜ | Interactive resume scoring | 0–100 match score with yellow-flag feedback areas |
| ⬜ | LinkedIn persona optimizer | AI-generated headlines and About sections |
| ⬜ | Job URL scraper | Paste a job posting URL instead of text — AI extracts the description |
| ⬜ | Multi-language CV translation | One-click translation of the full profile |
| ⬜ | Networking outreach generator | LinkedIn cold messages, recruiter emails, post-interview follow-ups |
| ⬜ | Salary negotiation AI | Market value research + customized negotiation scripts |
| ⬜ | AI interview coach (voice) | Practice elevator pitch using Web Speech API, get verbal feedback |

### Platform
| Status | Feature | Description |
|--------|---------|-------------|
| ✅ | SQLite support | Zero-config default database |
| ⬜ | PostgreSQL support | First-class support for production/shared deployments — change `DATABASE_URL` to `postgresql://...` and run `pip install psycopg2-binary` |
| ⬜ | Job application tracker (Kanban) | Visual board: Applied → Interviewing → Offer → Rejected, linked to generated documents |
| ⬜ | One-click portfolio generator | Export profile as a static HTML/CSS portfolio site |
