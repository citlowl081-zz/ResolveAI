# CLAUDE.md — ResolveAI (Claude Code Entry Point)

> **Note:** This file is the entry point for Claude Code. It references `AGENTS.md` for shared AI assistant rules. The two files must not conflict.

## Project: ResolveAI

An AI-powered e-commerce after-sales intelligent ticket agent. Portfolio project for AI Agent engineering interviews.

## Quick Reference

- **Read `AGENTS.md` first** — it contains rules shared across all AI coding tools.
- **Read `tasks/active-phase.md`** — it tells you which phase we're currently working on.
- **Read `docs/`** — architecture and design documents for deep context.

## Claude Code Specific Instructions

### Before Every Task
1. Read `AGENTS.md` (project rules).
2. Read `tasks/active-phase.md` (current phase).
3. Read the current phase task file (e.g., `tasks/phase-01-foundation.md`).
4. Read any relevant docs from `docs/`.
5. Check `git status` for uncommitted changes.
6. Output an implementation plan before writing code.

### After Every Phase Completion
1. Run all tests (`make test` or individual test commands).
2. Run linting (`make lint`).
3. Run type checking (`make typecheck`).
4. Fix any failures.
5. Update affected documentation.
6. Update task checklist.
7. Update `CHANGELOG.md`.
8. Generate a phase report in `reports/progress/`.
9. Suggest Git commit message.

### Code Style (Python)
- Match the surrounding code's comment density and naming style.
- Use `async/await` for all I/O operations.
- Type annotations on all function signatures.
- Pydantic v2 style: `model_validate()` not `parse_obj()`.
- SQLAlchemy 2 style: `select()` not `Model.query`.
- Use `ruff` for formatting and linting — no separate formatter configs.

### Code Style (TypeScript)
- Use functional components with hooks for React.
- Zod schemas for all API data validation.
- React Query for server state.
- shadcn/ui components via `npx shadcn-ui@latest add`.

### Testing
- pytest with `--strict-markers` and `-v`.
- Use `pytest.mark.asyncio` for async tests.
- Mock LLM calls — never call real APIs in tests.
- Use test fixtures from `backend/tests/fixtures/`.

### Git Workflow
- The project is NOT a fork — no upstream to worry about.
- Commit messages should be descriptive and reference the phase.
- Format: `[Phase NN] Brief description of changes`.
- Example: `[Phase 01] Set up FastAPI app with database models and migrations`.

## Environment

- **OS:** macOS (Darwin)
- **Shell:** zsh
- **Python:** 3.12+
- **Node:** 20+
- **Package Manager:** pip + npm
- **Database:** PostgreSQL 16 (via Docker)

## Key Constraints

- Phase 00: Planning only — no implementation code.
- Phases 01–06: No Redis, no MCP, no Kafka, no microservices.
- Always prioritize: runnable > testable > explainable > maintainable.
- This must be interview-ready: clean, documented, demonstrable.
