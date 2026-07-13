# ADR-001: Python 3.12 + FastAPI as Backend Framework

## Status
Accepted

## Context
We need a backend framework for the ResolveAI project. The backend must handle REST APIs, WebSocket connections for agent chat, database operations, and integration with LangGraph for the AI agent state machine.

## Decision
Use Python 3.12 with FastAPI as the web framework, SQLAlchemy 2 as the ORM, and Pydantic 2 for data validation.

## Alternatives Considered

### Node.js + Express/NestJS
- **Pros:** Same language as frontend, large ecosystem.
- **Cons:** LangGraph and the AI/ML ecosystem are Python-first. Using Node would require bridging or wrapping Python for the agent components.

### Go + Gin/Echo
- **Pros:** Excellent performance, static typing.
- **Cons:** Limited AI/ML library support. LangGraph, pgvector client libraries are Python-native. Would require gRPC bridge to Python agent service.

### Python + Django
- **Pros:** Mature, batteries-included, great admin.
- **Cons:** Heavier than needed. Django REST Framework adds complexity. Async support is less natural than FastAPI. Django ORM is less flexible than SQLAlchemy 2 for complex queries.

### Python + Flask
- **Pros:** Simple, lightweight.
- **Cons:** No built-in async support, no automatic OpenAPI docs, no built-in WebSocket support. Would need many extensions.

## Why FastAPI?
1. **Async-native:** Built on Starlette, natural async/await support — critical for I/O-bound agent operations and WebSocket connections.
2. **Pydantic integration:** Automatic request/response validation with the same Pydantic v2 we use throughout.
3. **Auto-generated OpenAPI docs:** `/docs` endpoint for development and testing.
4. **WebSocket support:** Built-in for agent chat.
5. **Dependency injection:** Clean pattern for auth checks, DB sessions, and service injection.
6. **LangGraph compatibility:** LangGraph and LangChain are Python-first and integrate seamlessly.

## Consequences

### Easier
- Type-safe API development with Pydantic models shared across API, services, and tools.
- Async database operations with SQLAlchemy 2 async sessions.
- Automatic API documentation for development and demo.
- Single-language backend — no Python/Node bridge needed.

### More Difficult
- Frontend and backend are in different languages (Python + TypeScript) — API types must be manually kept in sync or generated.
- Python's GIL limits CPU-bound parallelism (not a concern for I/O-bound agent work).

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
