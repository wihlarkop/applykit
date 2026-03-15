# ApplyKit

Self-hosted, local-first CV and cover letter generator powered by AI. Your data stays on your machine — no cloud, no account required.

## How It Works

```
Browser (localhost:5173)
       │
       ▼
  SvelteKit Frontend
  - Profile editor
  - CV preview & export
  - Cover letter editor
       │  HTTP (REST API)
       ▼
  FastAPI Backend (localhost:8000)
  - Profile CRUD (SQLite)
  - CV import (PDF/DOCX/text → LLM extraction)
  - ATS CV enhancement (LLM)
  - Cover letter generation (LLM)
  - PDF export (WeasyPrint)
       │
       ▼
  LiteLLM → Gemini API (or any LLM provider)
```

### Key Design Decisions

- **Single user, no auth** — designed for personal local use; profile is always `id=1`
- **API key lives in backend `.env` only** — never exposed to the browser
- **LLM is optional** — CV generation falls back to the raw profile if no API key is set; the status indicator in the header shows connection state
- **PDF export** — two options: server-side via WeasyPrint (requires GTK on Windows), or browser print/save as PDF (always works)
- **LiteLLM** — wraps any LLM provider using a unified API; swap Gemini for OpenAI, Anthropic, etc. by changing two env vars

---

## Project Structure

```
applykit/
├── backend/                  # FastAPI Python backend
│   ├── main.py               # App entrypoint, CORS, exception handlers
│   ├── app/
│   │   ├── models.py         # SQLAlchemy models (Profile)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── database.py       # SQLite session setup
│   │   ├── utils.py          # Shared helpers (model → schema)
│   │   ├── routes/
│   │   │   ├── profile.py    # GET/POST /api/profile, GET /api/status
│   │   │   ├── import_cv.py  # POST /api/import/cv
│   │   │   └── generate.py   # POST /api/generate/cv, /cover-letter, /*/pdf
│   │   └── services/
│   │       ├── llm.py        # LiteLLM wrapper (call_llm)
│   │       ├── parser.py     # PDF/DOCX/text extraction (pdfplumber, python-docx)
│   │       └── pdf.py        # WeasyPrint HTML→PDF (lazy import for Windows)
│   └── migrations/           # Alembic migration files
│
└── frontend/                 # SvelteKit TypeScript frontend
    └── src/
        ├── lib/
        │   ├── api.ts         # All API calls to the backend
        │   ├── types.ts       # TypeScript interfaces (mirrors backend schemas)
        │   └── components/
        │       ├── StatusIndicator.svelte  # Live API key connection status
        │       ├── CvPreview.svelte        # Print-ready CV layout
        │       ├── CoverLetterPreview.svelte
        │       └── ui/                    # shadcn-svelte components
        └── routes/
            ├── +layout.svelte        # Nav header + status indicator
            ├── +page.svelte          # Dashboard
            ├── profile/              # Profile editor
            ├── import/               # CV import (file upload or paste)
            ├── generate/             # CV generation + preview + export
            └── cover-letter/         # Cover letter generation + export
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/profile` | Get profile (`{profile: null}` if not set) |
| `POST` | `/api/profile` | Create or update profile |
| `GET` | `/api/status` | Check if API key is configured |
| `POST` | `/api/import/cv` | Extract profile from PDF/DOCX/text via LLM |
| `POST` | `/api/generate/cv` | ATS-enhance CV with LLM (falls back if no key) |
| `POST` | `/api/generate/cv/pdf` | Render CV HTML to PDF |
| `POST` | `/api/generate/cover-letter` | Generate cover letter from job description |
| `POST` | `/api/generate/cover-letter/pdf` | Render cover letter HTML to PDF |

Interactive docs available at `http://localhost:8000/docs` when the backend is running.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | SvelteKit 2 + Svelte 5 + TypeScript |
| Styling | Tailwind CSS v4 + shadcn-svelte |
| Backend | FastAPI + Python 3.12 |
| Database | SQLite via SQLAlchemy 2.0 + Alembic |
| AI | LiteLLM (default: `gemini/gemini-1.5-flash`) |
| PDF | WeasyPrint (server) + browser print (client) |
| CV parsing | pdfplumber (PDF), python-docx (DOCX) |
| Package managers | uv (Python), Bun (JavaScript) |

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Bun](https://bun.sh/) — JavaScript runtime
- A free [Google AI Studio](https://aistudio.google.com/) API key

---

## Setup

### 1. Backend

```bash
cd backend

# Copy and configure environment
cp .env.example .env
# Edit .env — set LLM_API_KEY and LLM_PROVIDER

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the server
uv run main.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 2. Frontend

```bash
cd frontend

bun install
bun run dev
# → http://localhost:5173
```

---

## Environment Variables

All variables go in `backend/.env` (never committed, never sent to the browser).

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini/gemini-1.5-flash` | LiteLLM model string |
| `LLM_API_KEY` | — | API key for the chosen provider |
| `DATABASE_URL` | `sqlite:///./applykit.db` | SQLite database path |

### Using a different LLM provider

LiteLLM supports OpenAI, Anthropic, Mistral, Ollama, and many others. Just change the two env vars:

```env
# OpenAI
LLM_PROVIDER=gpt-4o-mini
LLM_API_KEY=sk-...

# Anthropic
LLM_PROVIDER=claude-haiku-4-5-20251001
LLM_API_KEY=sk-ant-...

# Local Ollama (no API key needed)
LLM_PROVIDER=ollama/llama3.2
LLM_API_KEY=ollama
```

---

## Usage

1. **Set up your profile** — go to `/profile` and fill in your personal info, work experience, education, skills, and projects. Or use **Import CV** to auto-populate from an existing PDF/DOCX.

2. **Generate CV** — go to `/generate` and click Generate. If an API key is configured, the AI will rewrite your bullet points and summary to be ATS-optimized. Use **Print / Save PDF** to export directly from the browser.

3. **Write a cover letter** — go to `/cover-letter`, paste a job description, and click Generate. Copy the text or download as PDF.

The **status indicator** (top right) shows green when the backend is reachable and the API key is configured.
