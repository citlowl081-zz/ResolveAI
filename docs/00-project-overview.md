# 00 — Project Overview

## What is ResolveAI?

ResolveAI is a full-stack demonstration of an AI-powered after-sales service system for e-commerce. It simulates a real business environment where customers interact with an AI agent to resolve after-sales issues — refunds, exchanges, reshipments, logistics inquiries, and escalations to human support.

## Why This Project Exists

This project is designed as a portfolio piece for AI Agent engineering job interviews. It demonstrates:

1. **AI Agent Design** — How to structure an LLM-powered agent with explicit state machines, not just free-form ReAct loops.
2. **Tool Integration** — How to build, test, and observe tools that an agent calls to affect real business state.
3. **Safety & Control** — How to constrain an LLM agent with deterministic rules, approval gates, and audit trails.
4. **RAG** — How to build a retrieval-augmented generation system for policy documents.
5. **Memory** — How to maintain multi-tier memory across conversations.
6. **Full-Stack Integration** — How an AI agent fits into a real business application with a database, API, and frontend.

## Target Audience

- **Interviewers** evaluating AI/ML engineering candidates.
- **Fellow engineers** learning about AI agent architecture.
- **The builder (you)** demonstrating end-to-end AI application skills.

## Project Scope (v1.0)

### In Scope
- 5 after-sales intent types: logistics inquiry, pre-ship refund, post-delivery quality refund/exchange, missing parts reshipment, human escalation.
- Complete business backend with 17+ database tables.
- LangGraph-based agent state machine with 16 explicit nodes.
- pgvector-powered RAG with 15+ policy documents.
- Three-tier memory system.
- Human approval workflow for high-risk operations.
- Full audit logging and observability.
- Evaluation framework with 50+ test cases.
- Docker Compose deployment.

### Out of Scope (v1.0)
- Real payment gateway integration.
- Real logistics platform API integration.
- SMS/email notifications.
- WeChat mini-program.
- Merchant onboarding.
- Flash sales, recommendation systems.
- Kafka, microservices, Redis.
- OCR, voice support, knowledge graph.
- Multi-agent architectures beyond the single after-sales agent.

## Key Design Decisions

See `docs/decisions/` for Architecture Decision Records (ADRs).

1. **LangGraph over raw ReAct** — An explicit state machine gives us control, predictability, and debuggability.
2. **PostgreSQL + pgvector over dedicated vector DB** — Fewer moving parts; pgvector is sufficient for our scale.
3. **Deterministic rules + LLM** — The LLM handles natural language; code handles math and rules.
4. **Monolith backend** — One FastAPI app, not microservices. Simpler to develop, test, deploy, and explain.
5. **Synchronous HTTP + WebSocket for agent chat** — REST for CRUD, WebSocket for real-time agent conversation.

## Learning Path

This project is structured so you can explain it in an interview:

1. **The Problem:** E-commerce after-sales is repetitive, rule-based, and expensive to staff.
2. **The Approach:** An AI agent that understands natural language but follows deterministic business rules.
3. **The Architecture:** State machine, tools, RAG, memory, approval gates.
4. **The Safety Measures:** No LLM-makes-the-call on money; human-in-the-loop for high risk.
5. **The Results:** Evaluation metrics showing accuracy, safety, and efficiency.
