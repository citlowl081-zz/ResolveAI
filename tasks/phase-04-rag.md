# Phase 04 — RAG Knowledge Base

## Phase Goals

Implement the RAG system: policy document ingestion with embeddings, pgvector retrieval with metadata filtering, and integration with the agent's POLICY_RETRIEVAL node.

## Preconditions

- Phase 03 completed (agent tools and state machine).
- OpenAI API key configured (for embeddings).
- pgvector extension enabled (Phase 01).

## Task Checklist

### 4.1 Embedding Client
- [ ] `rag/embeddings.py` — OpenAI embedding client wrapper.
- [ ] Configurable model, dimensions, batch size.
- [ ] Error handling and retry.

### 4.2 Policy Document Management
- [ ] `rag/ingestion.py` — Load policies from `data/policies/`, chunk, embed, store.
- [ ] `rag/policy_service.py` — CRUD with re-embedding on update.
- [ ] `rag/versioning.py` — Create new version, supersede old.

### 4.3 Retrieval Pipeline
- [ ] `rag/retrieval.py` — Vector search + metadata filtering + reranking.
- [ ] `rag/query_gen.py` — LLM rewrites user message into search query.
- [ ] `rag/reranker.py` — Weighted scoring (vector + metadata + keyword).

### 4.4 Policy Data
- [ ] Create 15+ policy documents in `data/policies/`.
- [ ] Each policy as a Markdown file with metadata frontmatter.
- [ ] Policy categories: RETURN, REFUND, EXCHANGE, RESHIPMENT, LOGISTICS, RISK, SOP.

### 4.5 Integration
- [ ] `search_after_sales_policy` tool updates to use new RAG pipeline.
- [ ] POLICY_RETRIEVAL node uses query generation + retrieval.
- [ ] Empty results route to ESCALATED.
- [ ] Policy conflicts logged and flagged.

### 4.6 Admin API
- [ ] CRUD endpoints for policies.
- [ ] Status management (DRAFT → ACTIVE → SUPERSEDED → ARCHIVED).
- [ ] Policy preview (what would this policy match?).

### 4.7 Testing
- [ ] Embedding generation tests.
- [ ] Retrieval accuracy tests (Precision@5, Recall@5, MRR).
- [ ] Metadata filtering tests.
- [ ] Edge case tests: no results, expired policies, superseded policies.
- [ ] Ingestion idempotency tests.

## Acceptance Criteria

- [ ] 15+ policies ingested with embeddings.
- [ ] Vector search returns relevant policies for each intent type.
- [ ] Search latency < 500ms for top-5.
- [ ] Precision@5 >= 0.85 on test queries.
- [ ] Recall@5 >= 0.90 on test queries.
- [ ] Expired/superseded policies excluded from search.
- [ ] Empty results trigger ESCALATED routing.
- [ ] Admin can CRUD policies with automatic re-embedding.
- [ ] All tests pass.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
