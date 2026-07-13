# Active Phase

**Current Phase:** Phase 01 — Project Foundation

**Started:** 2026-07-13  
**Target Completion:** 2026-07-13  
**Status:** In Progress

## What This Phase Covers

- FastAPI app factory with configuration, health check, and database infrastructure.
- PostgreSQL 16 + pgvector via Docker Compose.
- Alembic initialization with pgvector extension (no business tables yet).
- Two Next.js frontend scaffolds (customer-web, admin-web).
- Testing infrastructure (pytest, Ruff, mypy).
- CI pipeline (GitHub Actions).
- Makefile with portable Python venv commands.

## What This Phase Does NOT Cover

- No business models, enums, JWT auth, product API, order API (→ Phase 02).
- No Service/Repository layers (→ Phase 02).
- No seed data (→ Phase 02).
- No Agent, RAG, Memory, Human Approval (→ Phases 03–06).

## Next Phase

Phase 02 — Business Backend: SQLAlchemy models, repositories, services, JWT auth, product/order API, seed data.
