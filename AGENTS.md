# AGENTS.md — ResolveAI AI Coding Assistant Rules

> **Audience:** All AI coding assistants (Claude Code, GitHub Copilot, Cursor, etc.) working on this project.

## Project Identity

**ResolveAI** is an AI-powered e-commerce after-sales intelligent ticket agent. It is a demonstration/portfolio project for AI Agent engineering roles, not a production SaaS.

## Core Principles

### 1. This Project Must Actually Run

- Every feature must have tests that pass.
- Every database change must have an Alembic migration.
- Every API change must be reflected in documentation.
- Never claim something is "done" without running tests and verifying they pass.

### 2. Phased Development Only

- This project is built in sequential phases (00–09).
- Read `tasks/active-phase.md` to know the current phase.
- Do NOT implement features from future phases.
- Each phase has explicit acceptance criteria that must be met before moving on.

### 3. Architecture Constraints

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, LangGraph, PostgreSQL + pgvector.
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui.
- **Deployment:** Docker, Docker Compose.
- **No microservices, no Kafka, no Redis (Phase 00–06).**
- Follow the layered architecture: API → Service → Repository → Database.
- Agent tools must call Service layer — never modify DB directly.

### 4. Separation of Concerns

- **LLM** handles: NLU, intent classification, entity extraction, summarization, natural language generation.
- **Code** handles: Calculations, database queries, rule evaluation, state validation, permission checks.
- **Database** is the source of truth for: users, orders, payments, logistics, tickets, refunds.
- The LLM must NEVER compute refund amounts, judge database state, or bypass approval checks.

### 5. Code Quality

#### Python
- Python 3.12 with full type annotations.
- Use `async/await` for I/O.
- Validate all external input with Pydantic.
- No bare `except:` — always catch specific exceptions.
- Functions must not exceed ~80 lines.
- `ruff check` must pass.
- `mypy --strict` must pass.
- `pytest` must pass with coverage.

#### TypeScript
- Strict mode enabled.
- Avoid `any` — use proper types or `unknown`.
- Validate external data with Zod.
- API types in a single shared location.
- `npm run lint` must pass.
- `npm run typecheck` must pass.
- `npm run build` must pass.

### 6. Testing Requirements

- Unit tests for repositories, services, rule engines, and tools.
- Integration tests for API endpoints and database operations.
- Agent node tests (each LangGraph node tested in isolation).
- Agent workflow tests (full graph execution with mocked LLM).
- End-to-end tests for critical user journeys.
- RAG retrieval tests (precision, recall, edge cases).
- Security tests (permissions, idempotency, prompt injection).
- Never delete failing tests to make CI pass.
- Never fabricate test results.

### 7. Database Changes

- All schema changes require an Alembic migration.
- Run `alembic revision --autogenerate` and review the output.
- Never modify a migration that has already been applied to any environment.
- Include both upgrade() and downgrade().
- Test migrations with `alembic upgrade head` and `alembic downgrade -1`.

### 8. Documentation Discipline

- Update `CHANGELOG.md` for every phase completion.
- Update `tasks/active-phase.md` when switching phases.
- Update relevant `docs/` files when designs change.
- Write ADRs in `docs/decisions/` for significant architectural choices.
- Keep `README.md` in sync with reality.

### 9. Security Rules

- Never log passwords, API keys, tokens, full phone numbers, or full addresses.
- Never hardcode secrets in code — use environment variables.
- All permissions must be enforced server-side, never client-side only.
- Sensitive operations require: permission check, input validation, idempotency key, transaction, audit log, and result verification.

### 10. Prohibited Actions

- ❌ Implement the entire project at once.
- ❌ Switch tech stack without discussion and documentation.
- ❌ Use `TODO` placeholders and claim completion.
- ❌ Use strings/dicts as a database replacement.
- ❌ Use keyword `if` statements as RAG replacement.
- ❌ Display tool calls in chat without actually executing them.
- ❌ Save raw chat history as the only memory.
- ❌ Let LLM compute refund amounts.
- ❌ Let LLM judge whether database operations succeeded.
- ❌ Let LLM bypass human approval.
- ❌ Skip tests and claim completion.
- ❌ Delete failing tests to pass CI.
