.PHONY: dev backend frontend install install-backend install-frontend migrate migration lint format test help

# ── Development ──────────────────────────────────────────────────

dev: ## Run backend and frontend concurrently
	@make -j2 backend frontend

backend: ## Run FastAPI backend (uvicorn with reload)
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run Vite dev server
	cd frontend && npm run dev

# ── Setup ────────────────────────────────────────────────────────

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install Python dependencies (editable + dev extras)
	cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

install-frontend: ## Install Node dependencies
	cd frontend && npm install

# ── Database ─────────────────────────────────────────────────────

migrate: ## Run alembic migrations
	cd backend && source .venv/bin/activate && alembic upgrade head

migration: ## Create a new migration (usage: make migration MSG="add friends table")
	cd backend && source .venv/bin/activate && alembic revision --autogenerate -m "$(MSG)"

# ── Quality ──────────────────────────────────────────────────────

lint: ## Run linters
	cd backend && source .venv/bin/activate && ruff check app/ tests/
	cd frontend && npm run lint

format: ## Auto-format code
	cd backend && source .venv/bin/activate && ruff format app/ tests/

test: ## Run all tests
	cd backend && source .venv/bin/activate && pytest -v

# ── Help ─────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
