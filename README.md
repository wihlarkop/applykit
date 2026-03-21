# ApplyKit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Self-hosted, local-first CV and cover letter generator powered by AI. Your data stays on your machine — no cloud, no account, no subscription.

---

## Features

- **Multi-profile support** — create separate profiles for different roles (e.g. "Software Engineer", "Product Manager"), each with its own history and color
- **AI CV generation** — rewrites bullet points and summary to be ATS-optimized for a specific job description
- **AI cover letter generation** — writes a tailored cover letter from your profile + job description in seconds
- **CV import** — paste or upload an existing PDF/DOCX and AI extracts your profile automatically
- **Job URL scraper** — paste a job posting URL and AI extracts the description
- **Fit analysis** — see how well your profile matches a job description with match score and gap analysis
- **Job application tracker** — track your applications through Applied → Interviewing → Offer → Rejected stages
- **History** — every generated CV and cover letter is saved and browsable, filterable by profile
- **PDF export** — download as PDF or use browser print (A4 format)
- **LLM-agnostic** — works with Gemini, OpenAI, Anthropic, Mistral, or any local model via Ollama
- **Works without an API key** — CV generation falls back to your raw profile data if no LLM is configured
- **Dark mode** — deep night theme with high-contrast accessibility variants

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
  - Fit analysis
  - Job tracker (Kanban)
  - History browser
       │  HTTP (REST API)
       ▼
  FastAPI Backend (localhost:8000)
  - Profile CRUD (SQLite, multi-profile)
  - CV import (PDF/DOCX/text → LLM extraction)
  - ATS CV enhancement (LLM)
  - Cover letter generation (LLM)
  - Fit score analysis (LLM)
  - Job URL scraping (crawl4ai)
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
| AI | LiteLLM (configured via UI Settings) |
| PDF | WeasyPrint (server-side) + browser print (client-side) |
| CV parsing | pdfplumber (PDF), python-docx (DOCX) |
| Job scraping | Jina Reader (primary) + Crawl4AI (fallback) + LLM parsing |
| Package managers | uv (Python), Bun (JavaScript) |

---

## Smart Apply - Supported Job Boards

Smart Apply can automatically extract job details from various job posting platforms:

### ATS Platforms with API Support (Fastest, Most Accurate)

| Platform | Status | Extracted Fields |
|----------|--------|------------------|
| Greenhouse | ✅ Supported | Company, Role, Location |
| Lever | ✅ Supported | Company, Role, Location |
| Ashby | ✅ Supported | Company, Role, Location |
| JazzHR | 📋 Planned | TBD |
| BambooHR | 📋 Planned | TBD |
| Workday | 📋 Planned | Requires browser automation (complex) |

### Generic Websites

For job boards without API access, Smart Apply uses Jina to scrape the page content and LLM to extract structured fields. This works on most websites.

### How Smart Apply Works

1. Paste a job URL → Smart Apply detects the platform
2. For Greenhouse/Lever/Ashby → Direct API extraction (fastest, most accurate)
3. For other sites → Jina scrape + LLM field extraction
4. For JS-heavy sites → Crawl4AI browser automation fallback

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager (`pip install uv` or see docs)
- [Bun](https://bun.sh/) — JavaScript runtime (`curl -fsSL https://bun.sh/install | bash`)
- **WeasyPrint system dependencies** (for PDF generation):
  - Ubuntu/Debian: `apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi7 shared-mime-info`
  - macOS: `brew install cairo pango gdk-pixbuf`
  - Windows: Included in WeasyPrint pip package
- An LLM API key (optional, for AI features):
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
```

### 3. Install backend dependencies

```bash
uv sync
```

> **Note:** WeasyPrint requires system libraries. On Ubuntu/Debian: `apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi7 shared-mime-info`

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

## Configuration

### Database

The only environment variable is the database path in `backend/.env`:

```env
DATABASE_URL=sqlite:///./applykit.db
```

### LLM Settings

LLM configuration (provider, API key) is managed via the **Settings** page in the UI — no need to edit `.env` manually.

Open the app and click **Settings** (gear icon) to configure:
- Provider (Gemini, OpenAI, Anthropic, Ollama, etc.)
- API key
- Model selection

> **No API key?** The app still works. CV generation falls back to your raw profile data without AI enhancement. Import, cover letter generation, and fit analysis require an API key.

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
> cp backend/.env.example backend/.env
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

### 5. Analyze job fit

1. Go to **Cover Letter** and paste a job description
2. Click **Analyze Fit** to see:
   - Match score (0-100%)
   - Strengths and gaps
   - Missing keywords
   - Suggested emphasis for your cover letter

### 6. Track applications

1. Go to **Tracker**
2. Add jobs you're applying to
3. Drag cards between columns: Applied → Interviewing → Offer → Rejected
4. Link generated CVs and cover letters to each application

### 7. Import an existing CV

1. Go to **Import CV** (or use AI Sync from the profile page)
2. Upload a PDF/DOCX file, or paste the text directly
3. The AI extracts all fields and populates your profile
4. Review and save

### 8. Browse history

Go to **History** to see every generated CV and cover letter. Filter by profile using the pill buttons at the top. Click any entry to preview it, regenerate from it, copy, print, or delete.

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
| ✅ | Dark mode | Deep Night theme with high-contrast accessibility variants |
| ⬜ | Real-time CV preview | Split-screen editor with live-updating preview |

### AI Features
| Status | Feature | Description |
|--------|---------|-------------|
| ✅ | ATS CV enhancement | AI rewrites bullet points and summary for a target job description |
| ✅ | Cover letter generation | Tailored cover letter from profile + job description |
| ✅ | CV import (PDF/DOCX) | AI extracts profile fields from an uploaded file |
| ✅ | Fit score analysis | 0–100 match score with strengths/gaps/missing keywords |
| ✅ | Job URL scraper | Paste a job posting URL instead of text — AI extracts the description |
| ⬜ | LinkedIn persona optimizer | AI-generated headlines and About sections |
| ⬜ | Multi-language CV translation | One-click translation of the full profile |
| ⬜ | Networking outreach generator | LinkedIn cold messages, recruiter emails, post-interview follow-ups |
| ⬜ | Salary negotiation AI | Market value research + customized negotiation scripts |
| ⬜ | AI interview coach (voice) | Practice elevator pitch using Web Speech API, get verbal feedback |

### Platform
| Status | Feature | Description |
|--------|---------|-------------|
| ✅ | SQLite support | Zero-config default database |
| ✅ | Job application tracker | Visual Kanban board for tracking applications |
| ⬜ | PostgreSQL support | First-class support for production/shared deployments — change `DATABASE_URL` to `postgresql://...` and run `pip install psycopg2-binary` |
| ⬜ | One-click portfolio generator | Export profile as a static HTML/CSS portfolio site |

### ATS Platform Support
| Status | Platform | Extracted Fields | Notes |
|--------|----------|------------------|-------|
| ✅ | Greenhouse | Company, Role, Location | Full API - fastest |
| ✅ | Lever | Company, Role, Location | Full API - fastest |
| ✅ | Ashby | Company, Role, Location | Full API - fastest |
| 📋 | JazzHR | TBD | API integration planned |
| 📋 | BambooHR | TBD | API integration planned |
| 📋 | Workday | TBD | Requires browser automation |

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
