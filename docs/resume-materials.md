# Resume & Portfolio Materials

## One-Line Project Description

Built a full-stack AI after-sales agent with LangGraph state machine, pgvector RAG policy retrieval, human-in-the-loop approval, and multi-session memory — 525 tests, 52 API endpoints, 3 frontend apps.

## 3 Key Contributions

1. **Designed and implemented a 9-node LangGraph agent** with tool calling, pending action confirmation flow, and deterministic rule engine integration — LLM handles NLU, code handles calculations and state validation.

2. **Built a RAG policy knowledge base** using pgvector exact cosine search with Chinese-friendly chunking, achieving HitRate@5=0.952 and zero citation fabrication across 21 evaluation queries.

3. **Implemented human-in-the-loop approval** with risk-based escalation, optimistic locking for concurrent decisions, payload integrity (DB-stored, not client-submitted), and idempotent execution resumption.

## 3 Project Highlights

1. **525 backend tests, 0 failures** — comprehensive coverage across unit, integration, E2E business scenarios, security, concurrency, and performance.

2. **Production-grade patterns** — optimistic locking, idempotency keys, short transaction boundaries, data minimization for LLM calls, PII stripping in logs, non-root Docker users.

3. **End-to-end demo** — 3 frontends (Next.js Customer + Admin + WeChat Mini Program), 52 REST endpoints, 20 database tables, 7 Alembic migrations, all running in Docker Compose with mock providers (zero API key setup).

## Tech Stack

Python 3.12 · FastAPI · LangGraph · SQLAlchemy 2 (async) · Pydantic 2 · PostgreSQL 16 · pgvector · Next.js 14 · TypeScript · Tailwind CSS · Docker · pytest · Playwright · Alembic · WeChat Mini Program

## Quantifiable Results

| Metric | Value |
|---|---|
| Backend tests | 525 (0 failures) |
| API endpoints | 52 |
| Database tables | 20 |
| LangGraph nodes | 9 |
| RAG HitRate@5 | 0.952 |
| RAG MRR | 0.775 |
| Citation fabrication | 0.000 |
| Memory write accuracy | 1.000 |
| Playwright E2E tests | 22 (Customer 14 + Admin 8, all passing) |
| Frontend apps | 3 (Customer + Admin + Mini Program) |
| Frontend routes | 34 total |

## Resume Version (3-4 lines)

**ResolveAI — AI-Powered E-Commerce After-Sales Agent**
- Built full-stack AI agent with LangGraph (9-node state machine), FastAPI backend (52 endpoints), and 3 frontend apps (Next.js + WeChat).
- Implemented pgvector RAG policy retrieval (HitRate@5=0.952), human-in-the-loop approval with optimistic locking, and multi-session memory system.
- 525 backend tests (0 failures), 22 Playwright E2E tests, Docker Compose demo with zero API key setup in the default mock configuration.

## Interview Self-Introduction (60 seconds)

"I built ResolveAI, a full-stack AI after-sales agent for e-commerce. The core is a 9-node LangGraph state machine that classifies user intent, retrieves relevant policies via pgvector semantic search, and proposes actions like refunds or exchanges. The LLM handles natural language understanding, but all calculations, eligibility checks, and state validations are done by deterministic Python code — the LLM never computes money or bypasses business rules.

High-risk operations go through a human-in-the-loop approval system with optimistic locking to prevent double-approval. The agent maintains long-term memory across sessions so it remembers customer preferences. I built the entire system end-to-end — the Python backend with 52 API endpoints, two Next.js frontends, a WeChat mini program, and a comprehensive test suite with 525 tests all passing. The whole thing runs in Docker Compose with mock providers by default, while an optional local demo can use Qwen through an OpenAI-compatible API."

## What NOT to Claim

- ❌ "Production deployed" (it's a local Docker Compose demo)
- ❌ "Real payment integration" (refunds are simulated)
- ❌ "Used Redis/Kafka" (explicitly excluded by design)
- ❌ "10x performance improvement" (no benchmark comparisons)
- ❌ "Used by real customers" (it's a portfolio project)
