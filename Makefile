# ============================================================
# ResolveAI - Makefile
# ============================================================

.PHONY: help install dev test lint typecheck build migrate clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---- Backend ----

install-backend: ## Install backend Python dependencies
	cd backend && pip install -e ".[dev]"

dev-backend: ## Run backend development server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test-backend: ## Run backend tests
	cd backend && pytest -v --cov=app --cov-report=term-missing

lint-backend: ## Run backend linter (Ruff)
	cd backend && ruff check app/ tests/

typecheck-backend: ## Run backend type checker (mypy)
	cd backend && mypy app/

migrate: ## Generate Alembic migration (autogenerate)
	cd backend && alembic revision --autogenerate -m "auto-migration"

migrate-up: ## Apply Alembic migrations
	cd backend && alembic upgrade head

migrate-down: ## Rollback last Alembic migration
	cd backend && alembic downgrade -1

# ---- Frontend ----

install-frontend: ## Install frontend dependencies
	cd frontend/customer-web && npm install
	cd frontend/admin-web && npm install

dev-frontend-customer: ## Run customer web dev server
	cd frontend/customer-web && npm run dev

dev-frontend-admin: ## Run admin web dev server
	cd frontend/admin-web && npm run dev

build-frontend: ## Build frontend for production
	cd frontend/customer-web && npm run build
	cd frontend/admin-web && npm run build

lint-frontend: ## Run frontend linter
	cd frontend/customer-web && npm run lint
	cd frontend/admin-web && npm run lint

typecheck-frontend: ## Run frontend type checker
	cd frontend/customer-web && npm run typecheck
	cd frontend/admin-web && npm run typecheck

test-frontend: ## Run frontend tests
	cd frontend/customer-web && npm run test
	cd frontend/admin-web && npm run test

# ---- Combined ----

install: install-backend install-frontend ## Install all dependencies

test: test-backend test-frontend ## Run all tests

lint: lint-backend lint-frontend ## Run all linters

typecheck: typecheck-backend typecheck-frontend ## Run all type checkers

check: lint typecheck test ## Run all checks (lint + typecheck + test)

# ---- Docker ----

docker-up: ## Start all services via Docker Compose
	docker compose up -d --build

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail Docker Compose logs
	docker compose logs -f

# ---- Clean ----

clean: ## Clean build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
