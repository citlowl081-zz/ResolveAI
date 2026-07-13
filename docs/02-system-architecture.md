# 02 — System Architecture

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        ResolveAI System                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │ Customer Web │   │  Admin Web   │   │   API Clients      │   │
│  │ (Next.js)    │   │  (Next.js)   │   │   (curl, etc.)     │   │
│  └──────┬───────┘   └──────┬───────┘   └────────┬───────────┘   │
│         │                  │                     │                │
│         └──────────────────┼─────────────────────┘                │
│                            │                                      │
│                    ┌───────▼──────────────────────────┐          │
│                    │     FastAPI Backend (Python)      │          │
│                    │                                   │          │
│  ┌─────────────────┼───────────────────────────────┐  │          │
│  │  API Layer       │  /api/v1/*                    │  │          │
│  │  - Auth Router   │  - Products Router             │  │          │
│  │  - Orders Router │  - Agent Router (WS + HTTP)    │  │          │
│  │  - Admin Router  │  - Tickets Router              │  │          │
│  └────────┬────────┘                                 │  │          │
│           │                                           │  │          │
│  ┌────────▼──────────────────────────────────────┐   │  │          │
│  │  Service Layer                                 │   │  │          │
│  │  - AuthService    - OrderService                │   │  │          │
│  │  - TicketService  - RefundService               │   │  │          │
│  │  - ApprovalService - PolicyService              │   │  │          │
│  │  - NotificationService                          │   │  │          │
│  └────────┬──────────────────────────────────────┘   │  │          │
│           │                                           │  │          │
│  ┌────────▼──────────────────────────────────────┐   │  │          │
│  │  Repository Layer                              │   │  │          │
│  │  - UserRepository  - ProductRepository          │   │  │          │
│  │  - OrderRepository - TicketRepository           │   │  │          │
│  │  - RefundRepository - PolicyRepository          │   │  │          │
│  └────────┬──────────────────────────────────────┘   │  │          │
│           │                                           │  │          │
│  ┌────────▼──────────────────────────────────────┐   │  │          │
│  │  Database (PostgreSQL + pgvector)              │   │  │          │
│  │  - Users, Products, Orders, Logistics          │   │  │          │
│  │  - Tickets, Refunds, Reshipments               │   │  │          │
│  │  - Policies (with vector embeddings)           │   │  │          │
│  │  - Agent Sessions, Memories, Audit Logs        │   │  │          │
│  └────────────────────────────────────────────────┘   │  │          │
│                                                         │  │          │
│  ┌─────────────────────────────────────────────────────┼──┘          │
│  │  Agent System (LangGraph)                           │             │
│  │                                                     │             │
│  │  ┌─────────────┐  ┌──────────┐  ┌───────────────┐ │             │
│  │  │ State        │  │ Tools    │  │ RAG Engine    │ │             │
│  │  │ Machine      │  │ (13+)    │  │ (pgvector)    │ │             │
│  │  │ (16 nodes)   │  │          │  │               │ │             │
│  │  └──────┬───────┘  └────┬─────┘  └───────┬───────┘ │             │
│  │         │               │                 │          │             │
│  │  ┌──────▼───────────────▼─────────────────▼───────┐ │             │
│  │  │  Memory System                                 │ │             │
│  │  │  - Short-term (session) - Long-term (user)      │ │             │
│  │  │  - Business State (cross-session)               │ │             │
│  │  └────────────────────────────────────────────────┘ │             │
│  └─────────────────────────────────────────────────────┘             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Backend Architecture

### Layered Architecture

```
API Router (FastAPI)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Database Access)
    ↓
Database (PostgreSQL)
```

**Rules:**
- API Router: Request parsing, auth checks, response formatting. No business logic.
- Service: Business rules, transactions, state management. Calls repositories and tools.
- Repository: Database read/write only. One repository per aggregate root.
- Agent Tools: Call Service layer. Never touch database directly.

### Agent Architecture

```
User Message
    ↓
LangGraph State Machine (16 nodes)
    ↓
LLM Calls (for NLU tasks)
    ↓
Tool Executor (wraps Service calls)
    ↓
Result Verification
    ↓
User Response
```

**Key Principle:** The agent is a state machine with LLM-powered nodes, NOT a free-form ReAct loop.

### Module Responsibility Matrix

| Module | Responsibility | Depends On |
|--------|---------------|------------|
| `api/` | HTTP/WS endpoints | `services/`, `schemas/` |
| `services/` | Business logic, transactions | `repositories/`, `rules/` |
| `repositories/` | Database queries | `models/` |
| `models/` | SQLAlchemy ORM models | `database/` |
| `schemas/` | Pydantic request/response schemas | — |
| `agent/` | LangGraph state machine | `tools/`, `rag/`, `memory/`, `llm/` |
| `tools/` | Agent-callable functions | `services/`, `schemas/` |
| `rag/` | Policy retrieval + embedding | `models/`, `llm/` |
| `memory/` | Session/user/business memory | `models/`, `repositories/` |
| `llm/` | LLM client abstraction | `config/` |
| `rules/` | Deterministic rule engine | — |
| `security/` | Auth, permissions, input sanitization | `config/` |
| `observability/` | Logging, tracing, audit | `models/` |
| `config/` | Settings from env vars | — |
| `database/` | Connection, session, migrations | `config/` |

## Data Flow: After-Sales Request

```
1. User sends message via WebSocket/HTTP
2. API Router authenticates user, creates/retrieves agent session
3. Agent State Machine starts (or resumes):
   a. INTENT_CLASSIFICATION → LLM classifies intent
   b. CUSTOMER_IDENTIFICATION → Loads user profile
   c. ORDER_RESOLUTION → Queries orders, resolves which order
   d. FACT_COLLECTION → Gathers order, logistics, ticket data
   e. POLICY_RETRIEVAL → RAG searches for applicable policies
   f. ELIGIBILITY_CHECK → Rule engine evaluates eligibility
   g. SOLUTION_GENERATION → LLM generates plan, code calculates amounts
   h. USER_CONFIRMATION → Agent presents plan, waits for confirmation
   i. RISK_CHECK → Rule engine evaluates risk level
   j. HUMAN_APPROVAL → If needed, pauses for admin approval
   k. ACTION_EXECUTION → Executes tools to create tickets/refunds/etc.
   l. RESULT_VERIFICATION → Checks database state post-execution
   m. MEMORY_UPDATE → Saves short-term, long-term, and business memory
   n. COMPLETED → Returns final result to user
4. Agent response sent to user
```

## Technology Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend framework | FastAPI | Async, Pydantic-native, auto-docs |
| ORM | SQLAlchemy 2 | Mature, async support, Alembic integration |
| Agent framework | LangGraph | Explicit state machine, checkpointing, streaming |
| Vector DB | pgvector | Same DB, fewer moving parts, sufficient for scale |
| LLM | Claude (Anthropic) | Strong tool use, structured output, safety |
| Frontend | Next.js 14 | React Server Components, app router, TypeScript |
| UI Components | shadcn/ui | Tailwind-compatible, copy-paste, customizable |
| State management | React Query | Server state caching, mutations, optimistic updates |
| Deployment | Docker Compose | Simple, reproducible, single-host |

## Port Allocation

| Service | Port |
|---------|------|
| Backend API | 8000 |
| Customer Web | 3000 |
| Admin Web | 3001 |
| PostgreSQL | 5432 |
