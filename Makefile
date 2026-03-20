.PHONY: install dev backend frontend migrate lint help

# ── Setup ─────────────────────────────────────────────────────────────────────

install: ## Install all dependencies (backend + frontend)
	cd backend && uv sync
	cd frontend && bun install

migrate: ## Run database migrations
	cd backend && uv run alembic upgrade head

# ── Development ───────────────────────────────────────────────────────────────

dev: ## Start both backend and frontend (requires two terminals, or use make backend / make frontend separately)
	@echo "Run 'make backend' and 'make frontend' in separate terminals."
	@echo "Or install 'concurrently': bun add -g concurrently && concurrently \"make backend\" \"make frontend\""

backend: ## Start the backend server (http://localhost:8000)
	cd backend && uv run main.py

frontend: ## Start the frontend dev server (http://localhost:5173)
	cd frontend && bun run dev

# ── Database ──────────────────────────────────────────────────────────────────

migrate-new: ## Create a new migration (usage: make migrate-new MSG="add column")
	cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Roll back the last migration
	cd backend && uv run alembic downgrade -1

# ── Code quality ──────────────────────────────────────────────────────────────

lint: ## Lint frontend TypeScript/Svelte
	cd frontend && bun run check

# ── Help ──────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
