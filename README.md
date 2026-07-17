# ResolveAI — AI-Powered E-Commerce After-Sales Agent

A full-stack demonstration of an LLM-based intelligent after-sales service agent built with LangGraph, FastAPI, PostgreSQL+pgvector, and Next.js. **Designed as a portfolio project for AI Agent engineering roles.**

## What It Does

A customer chats with an AI agent about an e-commerce order. The agent:
1. **Classifies intent** (refund, exchange, logistics inquiry, etc.)
2. **Looks up real data** — orders, logistics, after-sales policies via RAG
3. **Evaluates eligibility** using a deterministic rule engine (not the LLM)
4. **Retrieves policies** via pgvector semantic search with structured citations
5. **Proposes actions** — refund, reshipment, exchange
6. **Escalates high-risk cases** to human approval with pause/resume
7. **Remembers preferences** across sessions via long-term memory

## Demo Flow (5-minute walkthrough)

```
Customer logs in → views orders → opens agent chat
  → "I want a refund for these headphones"
  → Agent classifies intent: QUALITY_REFUND
  → Agent retrieves policy POL-REF-002 (citations shown)
  → Agent proposes refund action
  → Customer confirms
  → High refund amount triggers approval (shown: PENDING_APPROVAL)
  → Admin approves in admin dashboard
  → Refund executed, audit logged

Customer: "Remember I prefer Alipay for refunds"
  → Memory stored (PREFERENCE type)
  → Next session: preference loaded into context
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Pydantic 2 |
| Agent | LangGraph (9-node state machine) |
| LLM | OpenAI-compatible Qwen for local real demos; mock for CI/demo; optional Anthropic |
| Database | PostgreSQL 16 + pgvector |
| RAG | pgvector exact cosine similarity, Chinese-friendly chunking |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Mini Program | WeChat Native (TypeScript) |
| Testing | pytest (468 tests), Playwright E2E (15 specs) |
| Deployment | Docker, Docker Compose |

## Quick Start (Local Demo)

```bash
git clone <repo-url> && cd ResolveAI

# Start everything with one command (uses mock LLM, no API keys needed)
docker compose up -d

# Demo accounts (created by seed script):
#   Customer: demo@example.com / demo123456
#   Admin:    admin@example.com / admin123456

# Open:
#   Customer Web:  http://localhost:3000
#   Admin Web:     http://localhost:3001
#   Backend API:   http://localhost:8000/docs

# Stop:
docker compose down
```

## Architecture

```
┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
│ Customer Web │  │  Admin Web   │  │ WeChat Mini Prog │
│  (Next.js)   │  │  (Next.js)   │  │   (Native TS)    │
└──────┬───────┘  └──────┬───────┘  └────────┬────────┘
       │                 │                    │
       └─────────────────┼────────────────────┘
                         │ REST API
                 ┌───────┴────────┐
                 │   FastAPI      │
                 │  (Backend)     │
                 └───────┬────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────┴────┐    ┌──────┴──────┐   ┌────┴─────┐
   │ LangGraph│    │  Services   │   │   RAG    │
   │ 9 nodes  │    │ (12 classes)│   │ pgvector │
   └────┬────┘    └──────┬──────┘   └────┬─────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                 ┌───────┴────────┐
                 │  PostgreSQL 16 │
                 │  + pgvector    │
                 └────────────────┘
```

### LangGraph Agent Flow (9 nodes)

```
receive_message → load_session → build_context → classify_intent
    → select_tools → authorize_tool → execute_tool
        → (handle_tool_error) → compose_response
```

- **build_context:** Loads orders, tickets, messages, active memories
- **classify_intent:** LLM-based intent classification with keyword fallback
- **select_tools:** Maps intent to tool set (7 customer-facing tools)
- **execute_tool:** Calls Phase 02 Services (never modifies DB directly)
- **compose_response:** Generates response, builds citations, evaluates memory writes

### Tool Calling (7 tools)

`get_order`, `list_orders`, `get_logistics`, `get_after_sales_ticket`, `list_after_sales_tickets`, `create_after_sales_ticket`, `cancel_after_sales_ticket`, `search_after_sales_policy`

Write tools use `pending_action → confirm_action_id` flow — LLM proposes, user confirms, server executes.

### RAG Pipeline

```
Query → Embedding → pgvector <=> cosine search
    → SQL filters (category, status, effective date)
    → Dedup per policy_key → Deterministic sort
    → Citations (policy_key + version + snippet, no UUIDs)
```

### Human-in-the-Loop Approval

```
User confirms → Approval check (refund > threshold? risk HIGH? exchange?)
    → If triggers: create ApprovalTask, release turn, return PENDING_APPROVAL
    → Admin approves/rejects → Execute stored payload
    → Optimistic locking prevents double-approval
    → Tool idempotency prevents double-execution
```

## API Endpoints (52 total)

| Prefix | Count | Access |
|---|---|---|
| `/api/v1/auth` | 4 | Public |
| `/api/v1/products` | 2 | Authenticated |
| `/api/v1/orders` | 2 | CUSTOMER |
| `/api/v1/logistics` | 1 | CUSTOMER |
| `/api/v1/after-sales` | 6 | CUSTOMER |
| `/api/v1/agent` | 6 | CUSTOMER |
| `/api/v1/memories` | 5 | CUSTOMER |
| `/api/v1/approvals` | 2 | CUSTOMER |
| `/api/v1/admin/*` | 24 | OPERATOR/ADMIN |

## Project Structure

```
ResolveAI/
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── agent/         # LangGraph state machine
│   │   ├── api/v1/        # 52 REST endpoints
│   │   ├── models/        # SQLAlchemy models (20 tables)
│   │   ├── repositories/  # Data access layer
│   │   ├── services/      # Business logic (12 services)
│   │   ├── rules/         # Deterministic rule engines
│   │   ├── rag/           # Embedding, chunking, ingestion
│   │   └── security/      # JWT, RBAC, password hashing
│   ├── alembic/           # 7 migrations (001–007)
│   └── tests/             # 468 tests (unit + integration + eval)
├── frontend/
│   ├── customer-web/      # Next.js 14 customer portal (13 routes)
│   └── admin-web/         # Next.js 14 admin dashboard (9 routes)
├── miniprogram/           # WeChat Mini Program (12 pages)
├── docs/                  # Architecture & design documents
├── tasks/                 # Phase-based implementation plans
├── reports/               # Progress & evaluation reports
└── data/policies/         # 14 after-sales policy documents
```

## Testing & Evaluation

- **468 backend tests** (pytest, 0 failures)
- **15 Playwright E2E specs** (all passing)
- **RAG metrics:** HitRate@5=0.952, Precision@1=0.667, MRR=0.775, zero fabrication
- **Memory:** Write Accuracy 1.000, False-Write Avoidance 0.833
- **Security:** 14 RBAC/IDOR/PII tests passing
- **Concurrency:** Idempotency, dedup, optimistic locking all verified

## Key Design Decisions

1. **LLM never computes money** — refund amounts calculated by deterministic rule engine
2. **LLM never bypasses approval** — high-risk operations always create ApprovalTask
3. **No DB sessions during LLM/Embedding calls** — prevents connection leaks
4. **Optimistic locking** on all mutating entities (version column)
5. **Tool-level idempotency** via SHA256 hash, API-level via Idempotency-Key
6. **Data minimization** for LLM — field allowlists, PII stripped before external calls
7. **pgvector exact search** (no IVFFlat/HNSW) for deterministic retrieval results

## Environment Variables

See [.env.example](.env.example) for all configuration options.
Key settings:
- `LLM_PROVIDER=mock` — no API key needed for local demo
- `EMBEDDING_PROVIDER=mock` — no API key needed for local demo
- `LLM_PROVIDER=openai_compatible` + local `LLM_BASE_URL` and `LLM_API_KEY` — use Qwen through Bailian's OpenAI-compatible API
- `LLM_PROVIDER=anthropic` + `LLM_API_KEY` — optionally use Anthropic
- `EMBEDDING_PROVIDER=openai` + `EMBEDDING_API_KEY` — use real embeddings

## Known Limitations

1. No real payment gateway (refunds are simulated)
2. Mock LLM provider returns template responses (run `bash scripts/configure-qwen.sh` for a local real-LLM demo)
3. No Redis/Kafka/microservices (by design, Phases 00–06)
4. No WebSocket/SSE (agent uses sync HTTP request-response)
5. WeChat Mini Program requires WeChat Developer Tools for local testing
6. Not deployed to production cloud (Docker Compose for local demo)

## Future Extensions

- Real-time agent via WebSocket/SSE streaming
- Multi-language support
- Analytics dashboard with LLM cost tracking
- A/B evaluation framework for prompt optimization
- Cloud deployment (AWS ECS / Fly.io / Railway)

## License & Author

Educational/demonstration project. Developed as a portfolio for AI Agent engineering roles.
