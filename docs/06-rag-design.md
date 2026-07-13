# 06 — RAG Design

## Overview

The RAG system retrieves after-sales policies from a pgvector-backed knowledge base. It supports vector search with metadata filtering, versioning, and active-policy-only retrieval.

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    RAG System                           │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌──────────────────┐               │
│  │ Document     │    │  Query Pipeline  │               │
│  │ Ingestion    │    │                  │               │
│  │ Pipeline     │    │  User Message ───┤               │
│  │              │    │       │          │               │
│  │ Policy Text ─┼────┼─► Query Gen     │               │
│  │     │        │    │  (LLM rewrites  │               │
│  │  Chunking ───┼────┤   for search)   │               │
│  │     │        │    │       │          │               │
│  │  Embedding ──┼────┤  Vector Search  │               │
│  │     │        │    │  (pgvector)     │               │
│  │  Store ──────┼────┤       │          │               │
│  └─────────────┘    │  Metadata Filter│               │
│                      │       │          │               │
│                      │  Rerank (score) │               │
│                      │       │          │               │
│                      │  Top-K Return   │               │
│                      └──────────────────┘               │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Policy Document Store                │  │
│  │  policy_documents table (PostgreSQL + pgvector)   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└────────────────────────────────────────────────────────┘
```

## Policy Documents (v1.0)

The knowledge base includes at least 15 policy documents:

| # | Policy ID | Title | Category |
|---|-----------|-------|----------|
| 1 | POL-RET-001 | 通用退货规则 | RETURN |
| 2 | POL-REF-001 | 未发货退款规则 | REFUND |
| 3 | POL-REF-002 | 已发货退款规则 | REFUND |
| 4 | POL-REF-003 | 七天无理由退货规则 | RETURN |
| 5 | POL-REF-004 | 数码产品售后规则 | REFUND |
| 6 | POL-REF-005 | 食品类不可退规则 | REFUND |
| 7 | POL-EXC-001 | 服装换货规则 | EXCHANGE |
| 8 | POL-RES-001 | 缺件补发规则 | RESHIPMENT |
| 9 | POL-LOG-001 | 物流丢件赔付规则 | LOGISTICS |
| 10 | POL-REF-006 | 优惠券退款规则 | REFUND |
| 11 | POL-REF-007 | 运费退款规则 | REFUND |
| 12 | POL-RISK-001 | 高额退款审核规则 | RISK |
| 13 | POL-RISK-002 | 风险控制规则 | RISK |
| 14 | POL-SOP-001 | 人工客服处理SOP | SOP |
| 15 | POL-CASE-001 | 历史优秀工单案例001 | SOP |

## Policy Document Schema

```python
class PolicyDocument:
    policy_id: str          # e.g., "POL-REF-001"
    title: str              # e.g., "未发货退款规则"
    category: PolicyCategory # RETURN, REFUND, EXCHANGE, RESHIPMENT, LOGISTICS, RISK, SOP
    issue_type: str         # e.g., "PRE_SHIP_REFUND"
    content: str            # Full policy text
    content_summary: str    # Brief summary for display
    embedding: List[float]  # 1536-dimensional vector
    metadata_filter: dict   # Structured metadata for filtering
    effective_date: date    # When policy becomes active
    expiration_date: date   # When policy expires (optional)
    status: PolicyStatus    # DRAFT, ACTIVE, SUPERSEDED, ARCHIVED
    version: int            # Version number
    source: str             # Origin (e.g., "company_policy", "legal_requirement")
```

## Retrieval Pipeline

### Step 1: Query Generation

The user's message (which may be conversational and contain irrelevant details) is rewritten into a search-optimized query by the LLM.

```
User: "我那个白色的耳机昨天刚收到就不响了，这质量太差了我要退钱"

LLM query: "已收货 数码产品 质量问题 退款 耳机"
```

### Step 2: Vector Search

```sql
SELECT
    policy_id, title, category, content, content_summary,
    1 - (embedding <=> query_embedding) AS similarity
FROM policy_documents
WHERE status = 'ACTIVE'
  AND (expiration_date IS NULL OR expiration_date >= CURRENT_DATE)
  AND effective_date <= CURRENT_DATE
ORDER BY embedding <=> query_embedding
LIMIT $top_k;
```

### Step 3: Metadata Filtering

Additional filters applied based on intent:
```python
metadata_filters = {
    "category": intent_to_category(intent),  # e.g., "REFUND" for PRE_SHIP_REFUND
    "issue_type": intent,                     # e.g., "PRE_SHIP_REFUND"
}
```

### Step 4: Reranking

Results are reranked by a weighted score:
- Vector similarity (0.6 weight)
- Category match (0.2 weight)
- Keyword overlap (0.2 weight)

### Step 5: Top-K Return

Return top 5 policies with:
- `policy_id`
- `title`
- `content` (truncated to 500 chars for context)
- `similarity_score`
- `source_snippet` (the most relevant passage)

## Ingestion Pipeline

### Offline Ingestion

1. Load policy from `data/policies/*.md` or JSON files.
2. Split into chunks (if needed; most policies are short enough to be single chunks).
3. Generate embedding via OpenAI `text-embedding-3-small` (1536 dims).
4. Upsert into `policy_documents` table.

### Admin CRUD

- Admin creates/edits policy via admin web UI.
- On save: embedding is regenerated, version is incremented.
- Previous version is set to `SUPERSEDED`.

## Edge Cases & Safety

| Scenario | Behavior |
|----------|----------|
| **No results found** | Return empty list; agent routes to ESCALATED node |
| **Multiple conflicting policies** | Return all; agent routes to ESCALATED |
| **Policy is superseded** | Filtered out (status != ACTIVE) |
| **Policy not yet effective** | Filtered out (effective_date > today) |
| **Policy expired** | Filtered out (expiration_date < today) |
| **Embedding model unavailable** | Return error; agent routes to FAILED |
| **Query is vague** | LLM generates a broader search query |

## Evaluation

See `docs/09-testing-strategy.md` for RAG evaluation methodology.

Key metrics:
- **Precision@5:** % of top-5 results that are relevant.
- **Recall@5:** % of all relevant policies found in top-5.
- **MRR:** Mean Reciprocal Rank of the first relevant policy.

## Prohibited RAG Anti-Patterns

- ❌ Using keyword `if` statements as "RAG".
- ❌ Fabricating policies when none are retrieved.
- ❌ Stuffing all policies into the prompt without retrieval.
- ❌ Returning policies without source attribution.
- ❌ Using ChatGPT/Claude's training data as policy knowledge.
