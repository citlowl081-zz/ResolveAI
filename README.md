# ResolveAI — 基于大模型的电商售后智能工单Agent

**ResolveAI** is a full-stack demonstration project showcasing an AI-powered after-sales service agent for e-commerce. Built for AI Agent engineering job interviews, it integrates LLM-based natural language understanding, a deterministic rule engine, RAG-powered policy retrieval, a human approval workflow, and a complete business backend — all within a realistic simulated e-commerce environment.

## What ResolveAI Does

Users can browse products, place orders, check logistics, and initiate after-sales requests by chatting with an AI agent in natural language. The agent understands intent, looks up real order data, retrieves applicable policies, calculates refunds deterministically, creates tickets, and escalates high-risk cases for human approval — all while maintaining audit trails and memory across sessions.

## Key Features

- **AI After-Sales Agent** — LangGraph state machine with explicit nodes for intent classification, eligibility checks, solution generation, and action execution.
- **RAG Policy Knowledge Base** — pgvector-powered retrieval of after-sales policies with metadata filtering and versioning.
- **Multi-Tier Memory** — Short-term session memory, long-term user preferences, and business state memory for cross-session continuity.
- **Human Approval System** — Risk-based escalation with pause/resume for high-value refunds and sensitive operations.
- **Complete Business Backend** — Users, products, orders, logistics, after-sales tickets, refunds, and reshipments with full audit logging.
- **Observability** — Tool call logs, agent execution traces, and audit logs for every state-modifying operation.
- **Security** — Role-based access control, idempotency keys, input validation, PII masking in logs, and Prompt injection detection.
- **Evaluation Framework** — 50+ test cases with metrics for intent accuracy, tool selection, task completion, and safety.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2 |
| Agent | LangGraph (explicit state machine) |
| Database | PostgreSQL 16 + pgvector |
| RAG | pgvector embeddings + hybrid retrieval |
| Frontend (Customer) | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Frontend (Admin) | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Mini Program | WeChat Native Mini Program (planned) |
| Testing | pytest, React Testing Library |
| Deployment | Docker, Docker Compose |

## Quick Start

> **Note:** This project is under active development. See `tasks/active-phase.md` for current status.

```bash
# Clone the repository
git clone <repo-url>
cd resolve-ai

# Configure environment
cp .env.example .env
# Edit .env with your LLM API keys and database credentials

# Start all services
make docker-up

# Or run individually:
make dev-backend         # Backend on :8000
make dev-frontend-customer  # Customer web on :3000
make dev-frontend-admin     # Admin web on :3001

# Run tests
make test
```

## Project Structure

```
resolve-ai/
├── README.md               # This file
├── AGENTS.md               # AI coding assistant rules
├── CLAUDE.md               # Claude Code entry point
├── CHANGELOG.md            # Version history
├── .env.example            # Environment template
├── docker-compose.yml      # Container orchestration
├── Makefile                # Development commands
├── backend/                # Python backend (FastAPI + LangGraph)
├── frontend/               # Next.js frontends (customer + admin)
├── miniprogram/            # WeChat Mini Program (planned Phase 07)
├── docs/                   # Architecture & design documentation
├── tasks/                  # Phase-based task tracking
├── data/                   # Seed data, policies, evaluation cases
├── scripts/                # Utility scripts
└── reports/                # Progress reports
```

## Documentation

- [Project Overview](docs/00-project-overview.md)
- [Requirements](docs/01-requirements.md)
- [System Architecture](docs/02-system-architecture.md)
- [Database Design](docs/03-database-design.md)
- [API Contracts](docs/04-api-contracts.md)
- [Agent Workflow](docs/05-agent-workflow.md)
- [RAG Design](docs/06-rag-design.md)
- [Memory Design](docs/07-memory-design.md)
- [Security Design](docs/08-security-design.md)
- [Testing Strategy](docs/09-testing-strategy.md)
- [Deployment](docs/10-deployment.md)
- [Demo Script](docs/11-demo-script.md)

## License

This project is for educational and demonstration purposes.

## Author

Developed as a portfolio project for AI Agent engineering roles.
