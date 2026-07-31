#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DATABASE_URL="postgresql+asyncpg://resolveai_test:resolveai-test-only@localhost:5433/resolveai_test"

cd "$ROOT_DIR"
docker compose -f docker-compose.test.yml up -d --wait db-test

cd backend
export APP_ENV=test
export DATABASE_URL="$TEST_DATABASE_URL"
export TEST_DATABASE_URL="$TEST_DATABASE_URL"
export LLM_PROVIDER=mock
export LLM_API_KEY=""
export LLM_BASE_URL=""
export EMBEDDING_PROVIDER=mock
export EMBEDDING_API_KEY=""

source .venv/bin/activate
python -m pip check
python -m ruff check app/ tests/
python -m mypy --no-incremental app/ tests/
alembic upgrade head
python -m pytest "$@"

unset TEST_DATABASE_URL DATABASE_URL LLM_API_KEY LLM_BASE_URL EMBEDDING_API_KEY
