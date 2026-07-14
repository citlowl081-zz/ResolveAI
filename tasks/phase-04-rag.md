# Phase 04 — RAG Knowledge Base (Implementation Plan)

**Status:** Planning (revision 4 — final). Approved. Implementation not started.
**Date:** 2026-07-14
**Depends on:** Phase 03 (complete). Phases 02A/02B (complete).

---

## 1. Repository Audit (Current State)

### 1.1 What Exists

| Area | Status |
|---|---|
| pgvector extension | Enabled (migration 001, `CREATE EXTENSION IF NOT EXISTS vector`) |
| `policy_documents` table | **Not created.** No model, no migration. |
| `policy_chunks` table | **Not created.** |
| `policy_category` / `policy_status` enums | **Not created.** Neither PostgreSQL nor Python. |
| Embedding provider | Settings fields exist but need revision to OpenAI-compatible shape. **No ABC, no implementations.** |
| `rag/` module | **Does not exist.** |
| Policy data files | `data/policies/` directory exists but is **empty**. |
| `search_after_sales_policy` Agent tool | **Does not exist.** |
| Agent graph | 9 nodes. No RAG node. **Will stay at 9 nodes.** |
| Policy admin APIs | **Do not exist.** |
| RAG tests | `backend/tests/rag/` exists with only `__init__.py`. |

### 1.2 Key Constraints

1. pgvector is enabled — no new extension work.
2. Settings already declare embedding fields — will be revised to OpenAI-compatible shape.
3. CI must use `EMBEDDING_PROVIDER=mock` — zero real API keys.
4. LLM data minimization in `sanitization.py` — policy content must be projected.
5. Agent graph must NOT grow beyond 9 nodes — RAG goes through existing tool-execution path.
6. **Agent TX boundaries rule** (ADR in handoff): "Short UoW. No DB connections during LLM calls."
   This principle extends to embedding calls: **No DB session, transaction, or row lock may be open during any external embedding API call.**
7. Policy enums don't exist anywhere.

---

## 2. Phase Split and Scope

### 2.1 Phase 04A — Policy Knowledge Base

- `policy_documents` + `policy_chunks` SQLAlchemy models (policy_key + version keyed)
- `policy_category` + `policy_status` PostgreSQL enums + Python enums
- Alembic migration 005 (fixed `vector(1536)`)
- `EmbeddingProvider` ABC (OpenAI-compatible `/v1/embeddings` interface)
- `MockEmbeddingProvider` — deterministic, similarity-preserving, stable-hash vectors
- `OpenAICompatibleEmbeddingProvider` — httpx-based generic `/v1/embeddings` client
- `PolicyDocumentRepository` + `PolicyChunkRepository`
- `PolicyService` — CRUD, version state machine, concurrent-safe ingestion, search
- `PolicyIngestionService` — load from `data/policies/*.md` + `*.txt`, chunk, embed, upsert
- Chinese-friendly chunking (paragraph + sentence-boundary, character-budget, overlap by trailing sentences)
- Exact cosine similarity retrieval (no IVFFlat index)
- **Strict embedding transaction boundaries** — DB session fully closed before any `embed()` or `embed_query()` call
- Admin policy CRUD API endpoints
- 14 policy documents in `data/policies/` (no case studies)
- Document versioning with `UNIQUE(policy_key, version)`, at most one ACTIVE per key
- Idempotent ingestion by normalized content hash
- Concurrent ingestion safety via PostgreSQL advisory lock
- PostgreSQL integration tests

**Phase 04A gate:** All tests pass with `EMBEDDING_PROVIDER=mock`. Admin API completes CRUD and fixed-directory ingestion. `PolicyService.search()` returns correct results verified by real PostgreSQL + pgvector integration tests. No Agent integration. No vector search API endpoint (search is internal to PolicyService).

### 2.2 Phase 04B — Agent RAG Integration

- `search_after_sales_policy` Agent tool (allowed_roles = CUSTOMER only)
- **No new LangGraph node.** Tool is selected by `select_tools` like any other tool.
- `classify_intent` LLM prompt enriched to suggest policy search when relevant.
- Tool results flow into `tool_results` → `compose_response` generates structured `citations` array.
- `AgentResponse` extended with `citations` array (policy_key, version, title, category, snippet, similarity_score).
- No fabricated citations — citation must reference a retrieved policy_key + version.
- LLM data minimization for policy content (only summary + snippet sent to LLM).
- Retrieval trace via existing `agent_tool_logs` + `agent_traces`.
- Fallback: no policies found or results below min_similarity → `compose_response` states no applicable policy.
- RAG evaluation dataset: 20+ query/expected-policy_key pairs.
- RAG metrics: Precision@5, Recall@5, MRR. min_similarity threshold tuned from eval dataset.
- All existing Phase 02/03 tests (155+) continue to pass.

**Phase 04B gate:** Agent responds with grounded citations. Eval metrics pass thresholds. No graph node added. min_similarity tuned to a data-supported value.

### 2.3 Phase 04C — Document Upload (Optional, Deferred)

- PDF and DOCX parsing via `pdfplumber` or `python-docx` (exact libraries chosen during 04C scoping).
- Admin upload endpoint accepting multipart form upload.
- Extract text → chunk → embed → store as new policy version.
- Only scoped if needed. Does NOT block Phase 04A or 04B.

### 2.4 Explicit Exclusions

- No real embedding API keys in tests (use `MockEmbeddingProvider`)
- No Redis, Kafka, MCP, microservices
- No Phase 05 memory, Phase 06 HITL, Phase 07 frontend
- No keyword-if "RAG" — retrieval must go through pgvector `<=>` operator
- No fabricated policies when retrieval returns empty
- No new LangGraph node — use existing tool-execution path
- No PDF/DOCX in 04A or 04B
- No IVFFlat or ANN index in 04A (exact cosine; add separate migration when chunks > ~500)
- No case studies or historical work orders as formal policies
- No openai SDK dependency — use httpx directly

---

## 3. Database Schema and Migration

### 3.1 New Enums

```sql
CREATE TYPE policy_category AS ENUM (
    'RETURN', 'REFUND', 'EXCHANGE', 'RESHIPMENT',
    'LOGISTICS', 'RISK', 'SOP', 'GENERAL'
);

CREATE TYPE policy_status AS ENUM (
    'DRAFT', 'ACTIVE', 'SUPERSEDED', 'ARCHIVED'
);
```

Python in `app/models/enums.py`:

```python
class PolicyCategory(enum.StrEnum):
    RETURN = "RETURN"
    REFUND = "REFUND"
    EXCHANGE = "EXCHANGE"
    RESHIPMENT = "RESHIPMENT"
    LOGISTICS = "LOGISTICS"
    RISK = "RISK"
    SOP = "SOP"
    GENERAL = "GENERAL"

class PolicyStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"
```

### 3.2 `policy_documents` Table (Version-Per-Row)

Each version is a separate row. The stable business identity is `policy_key`.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, server_default gen_random_uuid() | Internal row PK — never exposed |
| policy_key | VARCHAR(50) | NOT NULL | Stable business key, e.g. `"POL-REF-001"` |
| version | INTEGER | NOT NULL, DEFAULT 1 | Monotonic per policy_key |
| title | VARCHAR(200) | NOT NULL | Human-readable title |
| category | policy_category | NOT NULL | |
| issue_types | JSONB | DEFAULT '[]' | e.g. `["PRE_SHIP_REFUND"]` |
| content | TEXT | NOT NULL | Full markdown/plain text |
| content_summary | TEXT | | 1-2 sentence summary for LLM context |
| content_hash | VARCHAR(128) | | BLAKE2b hex digest of normalized semantic fields (see §5.4) |
| metadata_filter | JSONB | DEFAULT '{}' | Structured eligibility conditions |
| effective_date | DATE | NOT NULL | |
| expiration_date | DATE | | NULL = no expiration |
| status | policy_status | NOT NULL, DEFAULT 'DRAFT' | |
| source | VARCHAR(100) | | e.g. `"company_policy"`, `"legal_requirement"` |
| superseded_by | UUID | FK → policy_documents.id, nullable | Points to the newer version row |
| created_at | TIMESTAMPTZ | NOT NULL, server_default NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, server_default NOW() | |

**Constraints:**
- `UNIQUE(policy_key, version)` — no duplicate versions for the same key.
- Partial unique index: `UNIQUE(policy_key) WHERE status = 'ACTIVE'` — at most one ACTIVE version per policy_key.
- `CHECK(version >= 1)`.

**Indexes:**
- `uq_policy_docs_key_version` UNIQUE (policy_key, version)
- `uq_policy_docs_key_active` UNIQUE (policy_key) WHERE status = 'ACTIVE'
- `ix_policy_docs_category` (category)
- `ix_policy_docs_status` (status)
- `ix_policy_docs_superseded_by` (superseded_by)

**Citation identity:** Citations reference `(policy_key, version)`, e.g. `"POL-REF-001" v2`. The internal UUID `id` is never exposed to clients or the LLM.

**Version history query:**
```sql
SELECT policy_key, version, title, status, effective_date, superseded_by
FROM policy_documents
WHERE policy_key = :key
ORDER BY version DESC;
```

### 3.3 `policy_chunks` Table

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, server_default gen_random_uuid() | |
| policy_document_id | UUID | FK → policy_documents.id, NOT NULL, ON DELETE CASCADE | Links to a specific version row |
| chunk_index | INTEGER | NOT NULL | 0-based position within that version |
| content | TEXT | NOT NULL | Chunk text |
| embedding | vector(1536) | NOT NULL | pgvector embedding |
| char_count | INTEGER | | Character count |
| created_at | TIMESTAMPTZ | NOT NULL, server_default NOW() | |

**Constraints:**
- `UNIQUE(policy_document_id, chunk_index)`

**Indexes:**
- `uq_policy_chunks_doc_idx` UNIQUE (policy_document_id, chunk_index)
- `ix_policy_chunks_doc_id` (policy_document_id)

No IVFFlat or ANN index. Exact cosine via `<=>` for current scale (~14 docs × ~2 chunks = ~28 rows).

### 3.4 Migration (005)

File: `backend/alembic/versions/005_create_policy_tables.py`

1. `CREATE TYPE policy_category AS ENUM (...)`
2. `CREATE TYPE policy_status AS ENUM (...)`
3. `CREATE TABLE policy_documents` with all columns, constraints, and indexes
4. `CREATE TABLE policy_chunks` with FK, UNIQUE, and indexes
5. **Vector dimension is fixed at `vector(1536)`** — not configurable at runtime

---

## 4. Embedding Architecture

### 4.1 EmbeddingProvider ABC

File: `backend/app/rag/embeddings.py`

```python
from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    """Async embedding provider with a fixed, declared dimension."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one vector per text."""
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension. Must match the database column (1536)."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier for logs/traces."""
        ...
```

### 4.2 MockEmbeddingProvider — Stable Deterministic Vectors

File: `backend/app/rag/mock_embeddings.py`

**Design goals:**
1. Similar texts produce vectors with higher cosine similarity.
2. Deterministic — same input always yields the same output.
3. Stable across Python process restarts — **must NOT use Python's built-in `hash()`** (randomized per process by `PYTHONHASHSEED`).
4. Zero external API calls.
5. Chinese-friendly — works on character bigrams without word segmentation.

**Algorithm: Character bigram feature hashing with BLAKE2b.**

#### Step 1: Text Normalization

Before bigram extraction, all input text is normalized:

```python
import re
import unicodedata

def _normalize(text: str) -> str:
    # Unicode NFKC (combining marks, fullwidth→halfwidth, etc.)
    t = unicodedata.normalize("NFKC", text)
    # ASCII lowercase
    t = t.lower()
    # Collapse all whitespace (spaces, tabs, newlines) to single space
    t = re.sub(r"\s+", " ", t)
    # Strip leading/trailing whitespace
    t = t.strip()
    # Remove control characters except common whitespace
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", t)
    return t
```

#### Step 2: Bigram Extraction

Character-level bigrams extracted from the normalized text:

```python
def _extract_bigrams(text: str) -> list[str]:
    """Extract character bigrams including start/end sentinels."""
    chars = list(text)
    if not chars:
        return []
    # Add sentinel bigrams for start and end
    bigrams = [f"^{chars[0]}"]
    for i in range(len(chars) - 1):
        bigrams.append(f"{chars[i]}{chars[i+1]}")
    bigrams.append(f"{chars[-1]}$")
    return bigrams
```

**Multi-language handling:**
- Chinese: `"订单退款"` → `["^订", "订单", "单退", "退款", "款$"]` — naturally captures 2-gram character patterns.
- English: `"order refund"` → `["^o", "or", "rd", "de", "er", "r ", " r", "re", ...]` — char bigrams work as a simple character n-gram model.
- Mixed: `"订单ABC退款"` → character boundaries are preserved across script boundaries.
- Single character: `"A"` → `["^A", "A$"]` — always produces at least 2 bigrams.
- Numbers/digits: `"100元"` → `["^1", "10", "00", "0元", "元$"]` — digits are treated as characters.
- Empty/whitespace-only: normalized to `""` → zero vector (all zeros).
- Punctuation-heavy: `"!!!"` → after normalization, characters remain as themselves; sentinel bigrams ensure minimum dimension coverage.

#### Step 3: BLAKE2b-Based Feature Hashing

Each bigram is hashed with BLAKE2b to produce a stable, deterministic index:

```python
import hashlib
import math

def _bigram_hash_vector(text: str, dimension: int) -> list[float]:
    normalized = _normalize(text)
    bigrams = _extract_bigrams(normalized)

    vec = [0.0] * dimension
    if not bigrams:
        return vec  # zero vector for empty text

    for bg in bigrams:
        # BLAKE2b produces a stable digest; 8 bytes → 64-bit unsigned int
        digest = hashlib.blake2b(bg.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest, "big") % dimension
        vec[idx] += 1.0

    # L2-normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec
```

**Why BLAKE2b instead of SHA256 or `hash()`:**
- `hash()` in Python is randomized per process via `PYTHONHASHSEED` — different runs produce different vectors.
- SHA256 is heavier than needed; BLAKE2b is faster and still cryptographically stable.
- `hashlib` is stdlib — no extra dependency.

**Similarity properties:**
- Texts sharing more bigrams → more hash collisions at same indices → higher cosine similarity.
- Normalization (NFKC + lowercasing + whitespace collapse) ensures `"订单退款"` and `"订单  退款"` produce the same bigrams.
- Tests must verify that `cosine("订单未发货退款", "订单未发货申请退款") > cosine("订单未发货退款", "物流查询规则")`.

### 4.3 OpenAICompatibleEmbeddingProvider

File: `backend/app/rag/openai_embeddings.py`

**Design:** Uses `httpx.AsyncClient` directly to call the OpenAI `/v1/embeddings` endpoint. Does NOT import `openai` SDK — avoids an unnecessary dependency.

**Protocol scope:** This provider is compatible with services that strictly follow the OpenAI `/v1/embeddings` request and response format (same JSON fields, same error shape). Claims of compatibility with Azure OpenAI or other vendors are deferred until tested against those specific services.

```python
class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        dimension: int,
        timeout: int = 60,
        max_retries: int = 1,
    ) -> None:
        ...
```

**Construction from settings:**
```python
import httpx
from app.config.settings import settings

def build_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider == "mock":
        return MockEmbeddingProvider(dimension=settings.embedding_dimension)

    if settings.embedding_provider == "openai":
        return OpenAICompatibleEmbeddingProvider(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            timeout=settings.embedding_timeout_seconds,
        )

    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider}")
```

**Dependency:** `httpx` is already a project dependency (used in tests). If `httpx` is imported directly in production code, verify it is declared as a direct runtime dependency in `pyproject.toml` (currently it's only in dev deps via `pytest-asyncio` — it should be moved to or duplicated in core dependencies).

### 4.4 Settings (Revise embedding block in `app/config/settings.py`)

| Env Var | Default | Description |
|---|---|---|
| `EMBEDDING_PROVIDER` | `"mock"` | `"mock"` or `"openai"` |
| `EMBEDDING_MODEL` | `"text-embedding-3-small"` | Model name sent in the API request body |
| `EMBEDDING_API_KEY` | `""` | API key (sent as `Authorization: Bearer <key>`) |
| `EMBEDDING_BASE_URL` | `"https://api.openai.com/v1"` | Base URL; `/embeddings` is appended |
| `EMBEDDING_DIMENSION` | `1536` | **MUST be 1536.** Any other value fails at startup. |
| `EMBEDDING_TIMEOUT_SECONDS` | `60` | Per-request timeout |
| `EMBEDDING_MAX_RETRIES` | `1` | Retry count for transient errors |
| `RAG_TOP_K` | `5` | Default top-K for retrieval |
| `RAG_MIN_SIMILARITY` | `None` (initial) | Minimum cosine similarity. **None = return all results.** Tuned in Phase 04B from eval data. |

### 4.5 Dimension Verification at Startup

```python
# In build_embedding_provider() or application startup:
provider = build_embedding_provider()
if provider.dimension != 1536:
    raise SystemExit(
        f"EMBEDDING_DIMENSION is {provider.dimension}, "
        f"but the database column is vector(1536). "
        f"Set EMBEDDING_DIMENSION=1536."
    )
```

**Rule:** `EMBEDDING_DIMENSION` is a configuration validation check, not a mechanism to change the database dimension. The database column is `vector(1536)` — period. Non-1536 values cause immediate startup failure.

---

## 5. Chunking Strategy (Chinese-Friendly)

### 5.1 Algorithm

File: `backend/app/rag/chunking.py`

```python
def chunk_text(
    text: str,
    max_chars: int = 500,
    overlap_chars: int = 50,
) -> list[str]:
    """Split text into overlapping chunks at natural boundaries.

    1. Split on paragraph breaks (\\n\\n+) first.
    2. Within each paragraph, split on Chinese sentence delimiters (。！？；) and
       ASCII equivalents (. ! ? ;).
    3. Greedy-merge sentences into chunks ≤ max_chars.
    4. Overlap: the last 1-2 complete trailing sentences from the previous chunk
       are prepended to the next chunk (total overlap ≈ overlap_chars).
    5. If a single sentence exceeds max_chars, perform a **character-level hard cut**
       at max_chars and continue. No sentence is un-chunkable.
    """
```

### 5.2 Detailed Steps

#### (a) Paragraph splitting
```
text → split on r'\n\s*\n' → paragraphs
```
Each paragraph is processed independently. Paragraph boundaries are natural semantic breaks.

#### (b) Sentence splitting within each paragraph
```
paragraph → split on r'(?<=[。！？；.!?;])\s*' → sentences
```
Each sentence is kept whole (including its delimiter).

#### (c) Greedy merge
```
chunk = []
for sentence in sentences:
    if len(''.join(chunk)) + len(sentence) <= max_chars:
        chunk.append(sentence)
    else:
        yield ''.join(chunk)    # finalize this chunk
        chunk = [sentence]       # start new chunk
if chunk:
    yield ''.join(chunk)
```

#### (d) Overlap by trailing sentences
When a chunk is finalized and a new chunk starts, prepend the last 1-2 complete sentences from the previous chunk whose combined length ≤ `overlap_chars`.

```
overlap_text = take_last_sentences_up_to(prev_chunk, max_chars=overlap_chars)
new_chunk = overlap_text + new_sentences
```

#### (e) Long-sentence hard cut
If a single sentence exceeds `max_chars` (e.g., a long unstructured paragraph without punctuation):
```
Hard split at max_chars boundary.
Continue splitting the remainder.
No overlap for hard-split segments (they're contiguous by definition).
```

This handles edge cases like policy documents with bullet lists, long tables, or missing punctuation.

### 5.3 Edge Cases

| Input | Behavior |
|---|---|
| Empty string | Returns `[]` |
| Whitespace only | Returns `[]` |
| Text shorter than max_chars | Returns single-chunk list |
| Single very long sentence | Hard-cut at max_chars boundaries |
| Text with only English | Sentence boundaries `. ! ?` apply; same algorithm |
| Mixed Chinese/English | Both delimiter sets apply; Unicode normalization handles mixed scripts |
| Text with no punctuation | Hard-cut at max_chars boundary |

### 5.4 content_hash Specification

The `content_hash` field stores a BLAKE2b hex digest of the **canonical JSON representation** of the following **semantic fields only**:

```python
import hashlib, json

def compute_content_hash(doc: dict) -> str:
    """Compute stable content hash over semantic fields only."""
    canonical = json.dumps({
        "title": doc["title"],
        "category": doc["category"],
        "issue_types": sorted(doc.get("issue_types", [])),
        "content": doc["content"],
        "content_summary": doc.get("content_summary", ""),
        "metadata_filter": _canonicalize_metadata(doc.get("metadata_filter", {})),
        "effective_date": str(doc["effective_date"]),
        "expiration_date": str(doc.get("expiration_date")) if doc.get("expiration_date") else None,
        "source": doc.get("source", ""),
    }, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    return hashlib.blake2b(canonical.encode("utf-8"), digest_size=32).hexdigest()
```

**Fields NOT included in hash:** `id`, `policy_key`, `version`, `status`, `superseded_by`, `created_at`, `updated_at`, any internal UUID, any database timestamps.

**Rationale:** Two rows with the same semantic content but different versions/history should produce the same hash. If content hasn't changed, ingestion is idempotent (skips).

---

## 6. Embedding Transaction Boundaries

### 6.1 Rule (Hard Constraint)

**No database session, transaction, or row lock may be open during any external embedding API call.**

This applies to BOTH:
- **Batch embedding** (`embed()`) during ingestion
- **Query embedding** (`embed_query()`) during search

This extends the existing Phase 03 ADR: "Agent TX boundaries: Short UoW. No DB connections during LLM calls."

### 6.2 Ingestion Flow (Three-Phase)

```
PHASE A — Read & Validate (short DB transaction):
  1. BEGIN
  2. SET LOCAL lock_timeout = '5s'
  3. Acquire advisory lock: pg_advisory_xact_lock(hashtext('policy_ingestion:' || policy_key))
     → Blocks up to lock_timeout. If timeout expires → PostgreSQL error → caught → 409 Conflict
  4. SELECT the latest version for this policy_key (MAX(version)) and its content_hash
  5. Compute content_hash from the candidate document's semantic fields (§5.4)
  6. Compare: if candidate hash == latest version hash → ROLLBACK, report "unchanged, skipped"
  7. Validate metadata fields, category, dates
  8. COMMIT
  (Advisory lock released on COMMIT. lock_timeout reset.)

PHASE B — Embed (NO database connection):
  9. chunk_text(content) → list of chunk strings
  10. Verify chunk list is non-empty
  11. Call EmbeddingProvider.embed(chunks) → list of vectors
  12. Verify len(vectors) == len(chunks)
  13. Verify each vector has dimension == 1536

PHASE C — Atomic Write (short DB transaction):
  14. BEGIN
  15. SET LOCAL lock_timeout = '5s'
  16. Re-acquire advisory lock: pg_advisory_xact_lock(hashtext('policy_ingestion:' || policy_key))
  17. Re-read the latest version number + latest row content_hash (may have changed since Phase A)
  18. Re-compare candidate hash vs. latest hash → if match now, ROLLBACK, report "unchanged (concurrent ingestion)"
  19. Determine new version = latest_version + 1
  20. INSERT new policy_documents row (version = new_version, status = DRAFT)
  21. INSERT all policy_chunks rows (one per chunk, with embedding)
  22. If the ingested document is marked activate=true:
      a. UPDATE the previous ACTIVE row (if any): SET status = 'SUPERSEDED', superseded_by = NEW.id
      b. UPDATE the new row: SET status = 'ACTIVE'
  23. COMMIT
  (Advisory lock released on COMMIT. lock_timeout reset.)
```

### 6.3 Search Flow (Two-Phase)

```
PHASE A — Embed Query (NO database connection):
  1. Call EmbeddingProvider.embed_query(user_query) → vector
  2. Verify dimension == 1536

PHASE B — Vector Search (short DB transaction, read-only):
  3. BEGIN (read-only)
  4. Execute vector search SQL (see §7)
  5. COMMIT
```

**No variant where `embed_query()` is called inside a transaction.**

### 6.4 Concurrent Ingestion Safety

**Scenario:** Two admin requests try to update the same `policy_key` concurrently.

**Protection mechanism:**

1. **PostgreSQL transaction-level advisory lock (blocking):** `pg_advisory_xact_lock(hashtext('policy_ingestion:' || policy_key))` acquired at the start of Phase A and Phase C. This is a **blocking** lock with a bounded `lock_timeout` of 5 seconds. If the lock cannot be acquired within 5 seconds, PostgreSQL raises an error → caught at application level → returned as HTTP 409 Conflict. The lock is automatically released on COMMIT/ROLLBACK.

2. **No infinite wait, no application-level retry loop.** The `lock_timeout` provides a hard upper bound. The caller (admin API endpoint) may retry the request, but the ingestion service itself does not loop.

3. **Re-read after lock:** Phase C re-reads the latest version number and its content_hash, which may have changed since Phase A (another transaction may have completed ingestion of the same key). The hash comparison is redone inside Phase C.

4. **UNIQUE constraints as final defense:**
   - `UNIQUE(policy_key, version)` — prevents two transactions from inserting the same version number (one will get an IntegrityError, surfaced as 409 Conflict).
   - `UNIQUE(policy_key) WHERE status = 'ACTIVE'` — prevents two ACTIVE rows for the same key.

5. **On IntegrityError in Phase C:** The transaction rolls back. The API returns 409 Conflict. The caller may retry the full request.

**Why advisory locks instead of `SELECT ... FOR UPDATE`?**
`FOR UPDATE` would require holding a DB transaction across Phase B (the embedding call), which violates the transaction boundary rule (§6.1). Advisory locks are released on COMMIT/ROLLBACK at the end of Phase A and re-acquired in Phase C — no lock is held during the external embedding call.

---

## 7. Version State Machine

### 7.1 States and Transitions

```
                    ┌─────────┐
          ┌────────>│  DRAFT  │
          │         └────┬─────┘
          │              │ activate
          │              ▼
          │         ┌─────────┐
  edit    │         │ ACTIVE  │──────────┐
 (creates │         └────┬─────┘          │ archive
  new     │              │                ▼
  DRAFT)  │              │ activate new  ┌────────────┐
          │              │ version       │ ARCHIVED   │
          │              ▼               └────────────┘
          │         ┌────────────┐
          └──────── │ SUPERSEDED │  (terminal)
                    └────────────┘
```

### 7.2 Transition Rules

| From | To | Trigger | Constraints |
|---|---|---|---|
| (none) | DRAFT | `POST /admin/policies` (default) | policy_key must not have an ACTIVE version (or allow alongside) |
| (none) | ACTIVE | `POST /admin/policies` with `status=ACTIVE` | Activate logic runs |
| DRAFT | ACTIVE | `PATCH .../versions/{version}/status` with `status=ACTIVE` | Atomically: old ACTIVE → SUPERSEDED (superseded_by = new.id), then new → ACTIVE. Target identified by (policy_key, version). |
| DRAFT | ARCHIVED | `PATCH .../versions/{version}/status` with `status=ARCHIVED` | Target identified by (policy_key, version). |
| ACTIVE | ARCHIVED | `PATCH .../versions/{version}/status` with `status=ARCHIVED` | Target identified by (policy_key, version). |
| ACTIVE | SUPERSEDED | System only — when a newer version is activated | `superseded_by` must point to the new ACTIVE row |
| _ | SUPERSEDED | System only — cannot be set directly via API | Terminal |
| _ | ARCHIVED | `PATCH .../status` (from DRAFT or ACTIVE only) | Terminal |

### 7.3 Key Rules

1. **New policy** via API: can be created as DRAFT (default) or explicitly ACTIVE.
2. **Editing an existing policy** via `PUT /admin/policies/by-key/{key}`: always creates a new **DRAFT** version. Does NOT automatically supersede the current ACTIVE.
3. **Activating a specific DRAFT** via `PATCH .../versions/{version}/status` with `status=ACTIVE`: the Service layer locates the row by `(policy_key, version)`. If found and in DRAFT status, atomically supersedes the old ACTIVE (if any) by setting its status to SUPERSEDED and linking `superseded_by`, then sets the target row to ACTIVE.
4. **Service layer must identify the target by (policy_key, version).** It must never implicitly select "the latest DRAFT" — the version must be explicit in the API path.
5. **SUPERSEDED and ARCHIVED are terminal states.** No further transitions allowed.
6. **Batch ingestion** from `data/policies/` can create DRAFT versions by default. Use `activate=true` flag to create them as ACTIVE (directly activating and superseding the prior ACTIVE).
7. **Search always filters `WHERE status = 'ACTIVE'`.**

---

## 8. Retrieval Pipeline

### 8.1 Exact Cosine Search (SQL)

File: `backend/app/rag/retrieval.py`

```sql
SELECT
    pd.policy_key,
    pd.version,
    pd.title,
    pd.category,
    pd.content_summary,
    pc.content AS snippet,
    pc.chunk_index,
    1 - (pc.embedding <=> :query_vec) AS similarity
FROM policy_chunks pc
JOIN policy_documents pd ON pc.policy_document_id = pd.id
WHERE pd.status = 'ACTIVE'
  AND (pd.expiration_date IS NULL OR pd.expiration_date >= CURRENT_DATE)
  AND pd.effective_date <= CURRENT_DATE
  AND (:category_filter IS NULL OR pd.category = :category_filter)
ORDER BY pc.embedding <=> :query_vec
LIMIT :max_candidates
```

### 8.2 Post-Query Processing (Python)

1. Discard results with `similarity < min_similarity` (if `min_similarity` is configured).
2. Group by `policy_key`.
3. Keep only the highest-similarity chunk per policy_key.
4. Sort by similarity descending.
5. Take the final `top_k`.

**Important ordering rules:**

| Rule | Location |
|---|---|
| Category filter | In SQL `WHERE` clause — before `ORDER BY` and `LIMIT` |
| Status filter (ACTIVE only) | In SQL `WHERE` clause |
| Effective/expiration date filter | In SQL `WHERE` clause |
| Cosine distance ordering | In SQL `ORDER BY` |
| Candidate limit (top_k × 3) | In SQL `LIMIT` |
| min_similarity threshold | In Python — after SQL returns |
| Dedup per policy_key (keep best chunk) | In Python |
| Final top_k slice | In Python |

**Nothing is filtered in Python that could have been filtered in SQL.** Category, status, and date filtering must precede the `ORDER BY` and `LIMIT` so that the database doesn't discard relevant rows before sorting.

### 8.3 min_similarity Threshold

| Setting | Phase 04A value | Phase 04B value |
|---|---|---|
| `RAG_MIN_SIMILARITY` | `None` (return all results regardless of score) | Tuned from eval dataset in Phase 04B |

**Do not hardcode a final threshold in 04A.** The threshold should be data-driven, established by measuring the similarity distribution on the eval dataset. Below-threshold results trigger the "no applicable policy" fallback in the Agent.

### 8.4 Retrieval as Internal Service

`PolicyService.search(query, category, top_k)` is an internal method called by:
- Integration tests (verify correctness)
- The Agent tool `search_after_sales_policy` (Phase 04B)

There is **no dedicated vector search REST API endpoint**. Admin policy management uses CRUD endpoints. Retrieval is tested through direct `PolicyService` calls in integration tests.

---

## 9. Document Ingestion and File Formats

### 9.1 Supported Formats (Phase 04A)

- **Markdown (`.md`)** — with YAML frontmatter for metadata
- **Plain text (`.txt`)** — with equivalent YAML frontmatter

### 9.2 YAML Frontmatter Specification

Every policy file in `data/policies/` consists of a YAML frontmatter block for metadata, followed by the policy body text. The two sections are separated by `---`.

```markdown
---
policy_key: POL-REF-001
title: 未发货退款规则
category: REFUND
effective_date: 2024-01-01
issue_types:
  - PRE_SHIP_REFUND
expiration_date: null
source: company_policy
content_summary: 未发货订单支持全额退款，包括商品金额和已支付运费。
metadata_filter:
  max_days_from_payment: null
  max_days_from_delivery: null
  applicable_categories: []
  excluded_categories: []
  requires_return_shipping: false
  requires_original_packaging: false
  max_refund_amount: null
  allowed_order_statuses: ["PENDING_PAYMENT", "PAID"]
  allowed_refund_types: ["FULL"]
  is_high_risk: false
  requires_human_approval: false
---

# 未发货退款规则

## 适用范围
订单状态为"待付款"或"已付款"但尚未发货的订单...

## 退款规则
1. 全额退款，包括商品金额和已支付的运费...
2. 退款将在1-3个工作日内原路返回...
```

**Parsing rules:**

1. The file is split on the first `---` that appears at the start of a line after the initial frontmatter delimiter.
2. The YAML frontmatter (between the first and second `---`) contains only metadata.
3. Everything after the second `---` is the **policy body** and becomes the `content` field.
4. Parsing uses `yaml.safe_load()` for the frontmatter.

**Required fields (in YAML frontmatter):** `policy_key`, `title`, `category`, `effective_date`

**Optional fields (in YAML frontmatter, with defaults):**
- `issue_types` → `[]`
- `content_summary` → auto-generated: first ~200 characters of the body text, normalized (collapsed whitespace, truncated at a word boundary). If the body is empty → validation error (see below).
- `expiration_date` → `null`
- `source` → `""`
- `metadata_filter` → `{}`

**Content (body text) validation:**
- The body text after the second `---` is **required** — an empty or whitespace-only body is a validation error.
- `content` is NOT a YAML field. It is never placed inside the frontmatter block.
- TXT files (`.txt`) use the same frontmatter + body format.

**Why `effective_date` is required:**
File modification time (`mtime`) is unstable across `git clone`, `cp`, CI checkouts, and Docker builds. Relying on mtime produces non-deterministic ingestion results. Requiring an explicit `effective_date` in the frontmatter eliminates this source of non-determinism.

**Validation rules:**
- `policy_key` must match the pattern `^POL-(RET|REF|EXC|RES|LOG|RISK|SOP|GEN)-\d{3}$`.
  The allowed prefixes correspond exactly to the `policy_category` enum values, and each prefix maps to exactly one category:
  - `RET` → RETURN
  - `REF` → REFUND
  - `EXC` → EXCHANGE
  - `RES` → RESHIPMENT
  - `LOG` → LOGISTICS
  - `RISK` → RISK
  - `SOP` → SOP
  - `GEN` → GENERAL
  All 14 planned policy files use keys matching this pattern. The pattern is enforced at the API schema level (Pydantic validator) and the Service layer.
- `category` must be a valid `policy_category` enum value, and must be consistent with the `policy_key` prefix (e.g., `POL-REF-*` must have `category = REFUND`).
- `issue_types` entries must be valid `intent_type` enum values (if provided).
- `effective_date` must be a valid ISO date string (required, see §9.2).
- `expiration_date` must be a valid ISO date string or `null`.
- `metadata_filter.allowed_order_statuses` entries must be valid `order_status` values.

**Parsing dependency:** YAML parsing requires the `PyYAML` library. This must be declared as a direct dependency in `pyproject.toml` (it is typically already present as a transitive dependency, but must be explicit). Alternatively, use Python's `tomllib`-style approach — but since we need YAML frontmatter, `PyYAML` or the stdlib's `yaml` (not available) must be declared.

Recommendation: Use `PyYAML>=6.0,<7` declared in `pyproject.toml` `[project] dependencies`.

### 9.3 Ingestion Source Directory

`POST /admin/policies/ingest` reads from a **fixed, server-side directory**:

```
<project_root>/data/policies/
```

The path is constructed from the application config, NOT from user input. The endpoint accepts no path parameter. This prevents path traversal attacks.

```python
# In PolicyIngestionService:
policies_dir = settings.policy_data_dir  # default: Path(__file__).resolve().parents[4] / "data" / "policies"
if not policies_dir.is_relative_to(settings.project_root):  # type: ignore[attr-defined]
    raise ValueError("Policy data directory outside project root")
```

### 9.4 Ingestion Idempotency

The idempotency check compares the candidate document's `content_hash` against **the latest version** of that `policy_key` (by `MAX(version)`), not just the ACTIVE version. This prevents duplicate DRAFT versions when the same file is ingested multiple times.

| Scenario | Behavior |
|---|---|
| File unchanged vs. latest version (ACTIVE or DRAFT) | **Skip entirely.** No new version created. Report: "unchanged". |
| File unchanged vs. ACTIVE but a later DRAFT exists with different content | New version created (version = latest+1) since content differs from latest. |
| File content changed (different content_hash from latest version) | **Create new version.** Phase C INSERT with version = latest+1. Status = DRAFT (or ACTIVE if activate=true). |
| File is new (policy_key not in DB) | **Create first version.** Version 1. Status = DRAFT (or ACTIVE if activate=true). |
| File content identical to an old historical version but different from latest | **Create new version** with version = latest+1. This is the intended mechanism for restoring old policy content. |
| File deleted from `data/policies/` but DB row exists | **No action.** Ingestion is additive. Deletion requires explicit API call (archive). |
| Two concurrent identical ingestions of the same file | Advisory lock serialises them. First creates the new version. Second sees matching content_hash against the now-latest version and skips. |

**Phase A and Phase C both read the latest version:**
- Phase A: `SELECT MAX(version) ... WHERE policy_key = :key` → compute candidate hash → compare.
- Phase C (after re-acquiring the advisory lock): re-read `MAX(version)` + the latest row → re-compare candidate hash. If the latest version's hash now matches the candidate (because another transaction created it in the interim), skip.

**Integration test coverage:**

- Candidate hash == latest ACTIVE hash → skip (no INSERT)
- Candidate hash == latest DRAFT hash → skip (no INSERT)
- Candidate hash != latest version hash → INSERT version+1
- Two concurrent identical ingestions → exactly one new version created, second skips
- Content matches a historical version but not the latest → new version created (restore)

---

## 10. Agent Integration (No New Graph Node)

### 10.1 Principle

Phase 03's 9-node graph stays at **9 nodes**. RAG uses the existing tool-execution path:

```
classify_intent → select_tools → authorize_tool → execute_tool → compose_response
```

### 10.2 How Policy Search Is Triggered

1. `classify_intent` LLM prompt is extended with a hint suggesting policy search for after-sales issues.
2. `select_tools` may include `search_after_sales_policy` in `planned_tools` when the intent suggests policy lookup.
3. `execute_tool` runs the tool → the result lands in `tool_results`.
4. `compose_response` reads `tool_results`, extracts policy search results, and produces the `citations` array.

### 10.3 New Tool: `search_after_sales_policy`

File: `backend/app/tools/definitions/search_after_sales_policy.py`

```python
class SearchAfterSalesPolicyTool(BaseTool):
    contract = ToolContract(
        tool_name="search_after_sales_policy",
        description=(
            "Search the after-sales policy knowledge base for policies "
            "relevant to a customer's issue. Returns matching policy "
            "titles, summaries, and relevant text snippets with scores."
        ),
        input_schema={...},
        allowed_roles={UserRole.CUSTOMER},
        is_mutating=False,
        audit_action="search_policy",
        underlying_service="PolicyService",
    )
```

**`allowed_roles` is CUSTOMER only.** Admin manages policies via the REST API, not via the Agent.

### 10.4 Structured Citations in Response

`AgentResponse` schema extended with:

```python
class Citation(BaseModel):
    policy_key: str        # e.g. "POL-REF-001"
    version: int           # e.g. 2
    title: str             # e.g. "未发货退款规则"
    category: str          # e.g. "REFUND"
    snippet: str           # Verbatim chunk text (≤ 300 chars)
    similarity_score: float

class AgentResponse(BaseModel):
    session_id: str
    message: str           # Natural language response
    citations: list[Citation] = []
    proposed_actions: list[dict] = []
```

**Client contract:** Clients receive `policy_key`, `version`, `title`, `category`, `snippet`, `similarity_score`. Internal UUIDs, `content_hash`, full `content` text, `metadata_filter`, and `superseded_by` are never exposed.

### 10.5 Citation Rules

1. Every citation must reference a real `(policy_key, version)` present in the tool result.
2. The `snippet` must be a verbatim substring of the retrieved chunk's `content` field from the database.
3. The LLM may paraphrase the policy in the `message` text, but the structured `citations` array is populated from tool output — not LLM generation.
4. If tool returns empty results (or all results below `min_similarity`) → `citations = []`, message states no applicable policy found.
5. No policy content may be fabricated by the LLM.

### 10.6 LLM Data Minimization for Policies

File: `backend/app/agent/sanitization.py` (extended):

```python
POLICY_LLM_FIELDS = frozenset({
    "policy_key", "title", "category", "content_summary",
    "snippet", "similarity_score",
})
```

Only `content_summary` and the best-matching `snippet` go to the LLM context — never the full `content` text.

### 10.7 Fallback Behavior

| Scenario | Behavior |
|---|---|
| Vector search returns 0 results | `tool_results` contains `{"policies": []}` → `citations = []` |
| All results below `min_similarity` | Filtered out in Python → result set empty → `citations = []` |
| Embedding provider unavailable | Tool returns error → `handle_tool_error` → graceful message without citations |
| `select_tools` does not include policy search | Normal Agent flow — no citations in response (not an error) |

---

## 11. API Endpoints

### 11.1 Admin Policy Management (Phase 04A)

All endpoints require `require_role("ADMIN")`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/admin/policies` | Create a new policy. Body includes `policy_key`, `title`, `category`, `content`, optional metadata. Default status = DRAFT. |
| `GET` | `/api/v1/admin/policies` | List policies, paginated. Query params: `category`, `status`, `page`, `page_size`. |
| `GET` | `/api/v1/admin/policies/by-key/{policy_key}` | Get the current ACTIVE version. Returns 404 (`POLICY_ACTIVE_NOT_FOUND`) if no ACTIVE version exists for this policy_key. Does NOT fall back to DRAFT, SUPERSEDED, or ARCHIVED. |
| `GET` | `/api/v1/admin/policies/by-key/{policy_key}/versions` | List all versions of a policy_key (paginated, ordered by version DESC). |
| `PUT` | `/api/v1/admin/policies/by-key/{policy_key}` | Update policy → creates new DRAFT version with incremented version number. |
| `PATCH` | `/api/v1/admin/policies/by-key/{policy_key}/versions/{version}/status` | Transition status for a specific version. Targets exactly `(policy_key, version)`. Body: `{"status": "ACTIVE"}`. Valid transitions: DRAFT→ACTIVE, DRAFT→ARCHIVED, ACTIVE→ARCHIVED. |
| `POST` | `/api/v1/admin/policies/ingest` | Trigger batch ingestion. Reads from fixed `data/policies/` directory. Body (optional): `{"activate": true}`. |

### 11.2 Security: Ingest Path

`POST /admin/policies/ingest` accepts an optional `activate` boolean in the request body. It does **NOT** accept a file path, directory path, or glob pattern. The source directory is hardcoded in the application config. This prevents path traversal attacks (e.g., `../../etc/passwd`).

### 11.3 Existing API Endpoints

**No changes.** Phase 04 is purely additive.

---

## 12. Security and Data Minimization

### 12.1 Policy Content Boundaries

- Policies are not tenant-scoped (single-merchant demo).
- No user PII in policy content.
- `search_after_sales_policy` tool output projected via `sanitization.py`.

### 12.2 Tool Authorization

- `search_after_sales_policy`: `allowed_roles = {UserRole.CUSTOMER}`.
  - Admin manages policies via REST API, not via Agent.
- Admin policy endpoints: `require_role("ADMIN")`.

### 12.3 Audit Trail

- Policy create/update/status-change → `audit_logs` row.
- `search_after_sales_policy` tool call → `agent_tool_logs` row (existing Phase 03 pattern).
- No new trace node needed — traces are captured by the existing `execute_tool` node tracing.

### 12.4 Embedding API Security

- API key via `EMBEDDING_API_KEY` (env var), never hardcoded.
- `EMBEDDING_PROVIDER=mock` in CI → zero external API calls.

---

## 13. Test Plan

### 13.1 Unit Tests (`tests/unit/rag/`)

| File | Count | Description |
|---|---|---|
| `test_chunking.py` | 7 | Chinese sentence-boundary chunking, paragraph splits, short docs, long-sentence hard cut, overlap, empty text, mixed Chinese/English |
| `test_mock_embeddings.py` | 6 | Deterministic output (same input → same vector), similar texts → higher cosine than dissimilar, single-char, empty text → zero vector, dimension=1536, hash stability across calls |
| `test_content_hash.py` | 3 | Same content → same hash, different status/version → same hash, different content → different hash |
| `test_retrieval.py` | 4 | Search returns results in correct order, category filter in SQL, status filter excludes non-ACTIVE, empty results |

### 13.2 Integration Tests (`tests/integration/rag/`)

| File | Count | Description |
|---|---|---|
| `test_policy_model.py` | 5 | UNIQUE(policy_key, version), active-partial-unique constraint, version lifecycle transitions, superseded_by FK, advisory lock |
| `test_policy_api.py` | 12 | Admin CRUD, auth required, validation errors (invalid policy_key prefix, prefix/category mismatch), version history endpoint, status transitions via explicit (policy_key, version), DRAFT→ACTIVE supersedes old ACTIVE, GET ACTIVE returns 404 when no ACTIVE, PATCH non-existent version → 404 |
| `test_policy_ingestion.py` | 12 | Ingest from files, unchanged vs. latest ACTIVE → skipped, unchanged vs. latest DRAFT → skipped, changed content → new DRAFT version, activate=true → new ACTIVE supersedes old, concurrent identical ingestion → exactly one new version, content matches historical but not latest → new version (restore), empty directory, invalid YAML → error, missing required field → error, body text empty → error, effective_date not in frontmatter → error |
| `test_policy_search.py` | 7 | Vector search accuracy, category filter, status filter, expired policy excluded, effective-in-future excluded, min_similarity threshold, search while no ACTIVE version exists |

### 13.3 RAG Evaluation (`tests/evaluation/rag/` — Phase 04B)

| File | Count | Description |
|---|---|---|
| `test_rag_metrics.py` | 3 | Precision@5, Recall@5, MRR against eval dataset |
| `eval_queries.json` | 20+ | Query → expected policy_keys (each query includes the natural-language text and expected matching policy_key list) |

### 13.4 Agent Integration Tests (Phase 04B)

| File | Count | Description |
|---|---|---|
| `test_rag_agent_tool.py` | 6 | Tool registered, tool output shape, citation structure, empty-results fallback, policy content projected through sanitization, CUSTOMER-only access |

### 13.5 Test Constraints

- `LLM_PROVIDER=mock` + `EMBEDDING_PROVIDER=mock` — zero real API keys.
- Integration tests use real PostgreSQL with pgvector.
- Self-contained: each test creates and cleans up its own data.
- Mock embedding bigram vectors provide meaningful similarity for retrieval testing.

### 13.6 Estimated Test Count

~62 new tests (20 unit + 36 integration + 6 agent + 3 evaluation).

---

## 14. File Modification Plan

### 14.1 New Files (Phase 04A)

```
backend/app/rag/
├── __init__.py
├── embeddings.py                  # EmbeddingProvider ABC
├── mock_embeddings.py             # MockEmbeddingProvider (BLAKE2b bigram hash)
├── openai_embeddings.py           # OpenAICompatibleEmbeddingProvider (httpx)
├── chunking.py                    # Chinese sentence-boundary chunking
├── ingestion.py                   # PolicyIngestionService (3-phase with advisory lock)
├── retrieval.py                   # Exact cosine search + result grouping

backend/app/models/
├── policy_document.py             # PolicyDocument (policy_key + version keyed)
├── policy_chunk.py                # PolicyChunk (embedding vector(1536))

backend/app/repositories/
├── policy_document.py             # PolicyDocumentRepository
├── policy_chunk.py                # PolicyChunkRepository

backend/app/services/
├── policy_service.py              # PolicyService (CRUD, version SM, concurrent-safe ingest, search)

backend/app/api/v1/
├── admin_policies.py              # Admin policy CRUD + ingest endpoint

backend/alembic/versions/
├── 005_create_policy_tables.py    # Migration: enums, tables, constraints, vector(1536)

backend/tests/
├── unit/rag/
│   ├── __init__.py
│   ├── test_chunking.py
│   ├── test_mock_embeddings.py
│   ├── test_content_hash.py
│   └── test_retrieval.py
├── integration/rag/
│   ├── __init__.py
│   ├── test_policy_model.py
│   ├── test_policy_api.py
│   ├── test_policy_ingestion.py
│   └── test_policy_search.py

data/policies/
├── POL-RET-001-通用退货规则.md
├── POL-REF-001-未发货退款规则.md
├── POL-REF-002-已发货退款规则.md
├── POL-REF-003-七天无理由退货规则.md
├── POL-REF-004-数码产品售后规则.md
├── POL-REF-005-食品类不可退规则.md
├── POL-EXC-001-服装换货规则.md
├── POL-RES-001-缺件补发规则.md
├── POL-LOG-001-物流丢件赔付规则.md
├── POL-REF-006-优惠券退款规则.md
├── POL-REF-007-运费退款规则.md
├── POL-RISK-001-高额退款审核规则.md
├── POL-RISK-002-风险控制规则.md
└── POL-SOP-001-人工客服处理SOP.md
```

14 policy files. No case studies. No historical work orders.

### 14.2 New Files (Phase 04B)

```
backend/app/tools/definitions/
├── search_after_sales_policy.py   # search_after_sales_policy Agent tool

backend/tests/
├── evaluation/rag/
│   ├── __init__.py
│   ├── test_rag_metrics.py
│   └── eval_queries.json
├── integration/rag/
│   └── test_rag_agent_tool.py
```

### 14.3 Modified Files

| File | Change | Phase |
|---|---|---|
| `backend/app/models/__init__.py` | Add PolicyDocument, PolicyChunk | 04A |
| `backend/app/models/enums.py` | Add PolicyCategory, PolicyStatus | 04A |
| `backend/app/config/settings.py` | Revise embedding block + add `RAG_TOP_K`, `RAG_MIN_SIMILARITY` | 04A |
| `backend/app/api/__init__.py` | Include admin_policies router | 04A |
| `backend/pyproject.toml` | Add `httpx` to core deps, add `PyYAML>=6.0,<7` | 04A |
| `backend/app/tools/definitions/__init__.py` | Register SearchAfterSalesPolicyTool | 04B |
| `backend/app/agent/sanitization.py` | Add `POLICY_LLM_FIELDS`, `project_policy_for_llm` | 04B |
| `backend/app/agent/nodes/classify_intent.py` | Extend LLM prompt to suggest policy search | 04B |
| `backend/app/agent/nodes/compose_response.py` | Build `citations` array from tool_results | 04B |
| `backend/app/schemas/agent.py` | Add Citation model, extend response schema | 04B |

### 14.4 Files NOT Modified

- `backend/app/agent/graph.py` — stays at 9 nodes
- `backend/app/agent/routing.py` — no new routes
- `backend/app/agent/state.py` — no new state fields (policies flow through tool_results)
- All Phase 02A/02B services and repositories
- All existing API endpoints
- All existing tests

---

## 15. Implementation Order and Local Commits

### Commit 1: Enums + Settings + Data Model (04A)
- Add `PolicyCategory`, `PolicyStatus` to `enums.py`
- Revise embedding settings to OpenAI-compatible shape
- Add `RAG_TOP_K`, `RAG_MIN_SIMILARITY` to settings
- Create `PolicyDocument`, `PolicyChunk` SQLAlchemy models
- Update `models/__init__.py`
- Create migration 005 (fixed vector(1536), UNIQUE constraints, partial active index)
- Add `httpx` and `PyYAML` to pyproject.toml dependencies
- Migration cycle test (upgrade/downgrade)
- `ruff check`, `mypy`

### Commit 2: Embedding Providers + Chunking (04A)
- `EmbeddingProvider` ABC
- `MockEmbeddingProvider` (BLAKE2b bigram feature hash with NFKC normalization)
- `OpenAICompatibleEmbeddingProvider` (httpx, no openai SDK)
- `chunking.py` (paragraph + sentence boundaries, char budget, overlap by trailing sentences, long-sentence hard cut)
- `content_hash` function (BLAKE2b over canonical JSON of semantic fields)
- Unit tests: chunking, mock embeddings, content hash
- `ruff check`, `mypy`, `EMBEDDING_PROVIDER=mock pytest tests/unit/rag/ -v`

### Commit 3: Repositories + Retrieval (04A)
- `PolicyDocumentRepository`, `PolicyChunkRepository`
- `retrieval.py` (exact cosine, category/status/date in SQL, result grouping in Python)
- Unit tests: retrieval
- `ruff check`, `mypy`, tests

### Commit 4: Service + Ingestion + Admin API (04A)
- `PolicyService` (CRUD, version state machine, concurrent-safe 3-phase ingest with advisory lock, search)
- `PolicyIngestionService` (file scanning, YAML frontmatter parsing, embed→save)
- `admin_policies.py` API router (7 endpoints)
- Register router
- Integration tests: model constraints, API, ingestion, search
- Ingestion tests: same content → skipped, changed content → new version, activate=true → direct ACTIVE
- `ruff check`, `mypy`, `EMBEDDING_PROVIDER=mock pytest -v`

### Commit 5: Policy Data Files (04A)
- Write 14 policy Markdown files with YAML frontmatter
- Test end-to-end ingestion → search with mock embeddings
- `ruff check`, `mypy`, all tests

### Commit 6: Agent Tool + Citations (04B)
- `SearchAfterSalesPolicyTool` + registration
- Citation model in schemas
- `compose_response` citation builder
- `classify_intent` prompt extension
- `sanitization.py` policy projection
- Agent integration tests
- All 155 Phase 02/03 tests must still pass
- `ruff check`, `mypy`, full test suite

### Commit 7: RAG Evaluation (04B)
- `eval_queries.json` (20+ query → expected policy_keys)
- Evaluation metrics (Precision@5, Recall@5, MRR)
- Tune `RAG_MIN_SIMILARITY` from eval data
- Citation accuracy verification (no fabricated citations)
- Phase 04 handoff documentation
- `ruff check`, `mypy`, `LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock pytest -v`
- Update `tasks/active-phase.md`, `reports/progress/current-handoff.md`, `CHANGELOG.md`

---

## 16. Risks and Decisions

### 16.1 Resolved Decisions

| Decision | Resolution |
|---|---|
| Version model | `UNIQUE(policy_key, version)`. One row per version. At most one ACTIVE per key. |
| Agent graph | No new node. RAG uses existing tool-execution path. 9 nodes unchanged. |
| Mock embeddings | Character bigram feature hash via BLAKE2b. NFKC normalization. No `hash()`. |
| Chunking | Paragraph → sentence delimiters (。！？；.!?;) → greed merge → overlap by trailing sentences → hard cut for long single sentences. |
| ANN index | Deferred. Exact cosine `<=>`. Add migration when chunks > ~500. |
| Embedding TX boundary | No DB session during ANY embedding call (ingestion or search). Three-phase ingestion. Two-phase search. |
| Concurrent safety | `pg_advisory_xact_lock` (blocking, `lock_timeout = 5s`) + re-read-after-lock in Phase C + hash re-compare + UNIQUE constraints as final defense. No application-level retry loop. |
| Citations | Structured `citations` array. policy_key + version exposed. UUIDs and hashes never exposed. |
| Provider interface | OpenAI-compatible `/v1/embeddings` via httpx. No openai SDK. |
| Vector dimension | Fixed at 1536 in migration. Non-1536 EMBEDDING_DIMENSION fails at startup. |
| search_after_sales_policy roles | CUSTOMER only. Admin uses REST API. |
| Case studies | Excluded from Phase 04. |
| File formats | Markdown + TXT in 04A. PDF/DOCX deferred to 04C. |
| Phase split | 04A (KB + retrieval) → gate → 04B (agent + eval) → done. 04C optional. |
| Version state machine | Edit → new DRAFT. Activate specific (policy_key, version) → SUPERSEDE old ACTIVE. Archive from DRAFT/ACTIVE. SUPERSEDED/ARCHIVED terminal. No implicit "latest DRAFT" selection. |
| content_hash | BLAKE2b over normalized semantic fields (9 fields). Excludes status/version/UUID/timestamps. Compared against latest version (not just ACTIVE). |
| Ingest path | Fixed `data/policies/` directory. No user-supplied path. |
| Retrieval API | Internal to PolicyService. No REST endpoint. Tested via integration tests. |
| min_similarity | Configurable. None in 04A (return all). Tuned from eval data in 04B. |
| policy_key validation | Explicit prefix set: `POL-(RET\|REF\|EXC\|RES\|LOG\|RISK\|SOP\|GEN)-\d{3}`. Prefix must match category. |
| ACTIVE query | `GET /by-key/{key}` returns ACTIVE only. No ACTIVE → 404. DRAFT/SUPERSEDED/ARCHIVED only via versions endpoint. |
| File format | YAML frontmatter (metadata only) + body text after `---`. `content` is the body, never in YAML. `effective_date` required in frontmatter. |

### 16.2 Deferred Decisions

1. **LLM query rewriting** — raw user query → vector search. Revisit if retrieval quality is poor.
2. **Reranker** — cosine similarity only.
3. **Hybrid search (keyword + vector)** — vector-only at current scale.
4. **IVFFlat / ANN index** — add migration when chunks exceed ~500 rows.
5. **PDF/DOCX parsing** — Phase 04C only if needed.
6. **Azure OpenAI compatibility** — not claimed; test before claiming.

---

## 17. Acceptance Criteria

### Phase 04A
- [ ] `policy_documents` + `policy_chunks` tables created (migration 005, `vector(1536)` fixed)
- [ ] `UNIQUE(policy_key, version)`, partial `UNIQUE(policy_key) WHERE status = 'ACTIVE'`
- [ ] `PolicyCategory` + `PolicyStatus` enums in PostgreSQL and Python
- [ ] `EmbeddingProvider` ABC + `MockEmbeddingProvider` (BLAKE2b bigram hash, NFKC normalization, stable across restarts) + `OpenAICompatibleEmbeddingProvider` (httpx, no openai SDK)
- [ ] Chinese-friendly chunking (paragraph → sentence delimiters → greed merge → overlap by sentences → hard cut for long sentences)
- [ ] `content_hash` covers 9 semantic fields; excludes status/version/UUID/timestamps
- [ ] 14 policy documents ingested with embeddings
- [ ] Exact cosine search returns relevant policies
- [ ] SQL WHERE filters category, status, and date before ORDER BY and LIMIT
- [ ] Admin CRUD API (7 endpoints), auth enforced
- [ ] `GET /by-key/{policy_key}` returns ACTIVE only; 404 when no ACTIVE exists
- [ ] `PATCH /by-key/{policy_key}/versions/{version}/status` targets exact (policy_key, version)
- [ ] `policy_key` validated against explicit prefix set (RET/REF/EXC/RES/LOG/RISK/SOP/GEN), prefix consistent with category
- [ ] `POST /admin/policies/ingest` reads only from fixed `data/policies/` directory
- [ ] Idempotent ingestion: unchanged vs. latest version → skipped; changed vs. latest → new version; concurrent identical → exactly one new version
- [ ] Version state machine: edit → new DRAFT; activate specific (policy_key, version) → SUPERSEDE old; archive; SUPERSEDED/ARCHIVED terminal
- [ ] Concurrent ingestion safe: `pg_advisory_xact_lock` with `lock_timeout = 5s` + re-read + hash re-compare + UNIQUE defense
- [ ] Policy files: YAML frontmatter (metadata) + body text (content). `effective_date` required in frontmatter. Body text required.
- [ ] Embedding TX boundaries: no DB session open during any `embed()` or `embed_query()` call
- [ ] Dimension verification at provider startup (non-1536 → SystemExit)
- [ ] `EMBEDDING_PROVIDER=mock` — all tests pass, zero real API keys
- [ ] `ruff check` PASS, `mypy` PASS, `pytest -v` PASS

### Phase 04B
- [ ] `search_after_sales_policy` tool registered, `allowed_roles = {CUSTOMER}`
- [ ] Agent graph unchanged (9 nodes)
- [ ] `classify_intent` prompt extended for policy search suggestion
- [ ] `compose_response` produces structured `citations` array
- [ ] Citations contain: policy_key, version, title, category, snippet, similarity_score — no UUIDs, no content_hash
- [ ] No fabricated citations (eval test verifies)
- [ ] Fallback when no policies found or all below min_similarity
- [ ] Policy content projected through `sanitization.py` before LLM
- [ ] `RAG_MIN_SIMILARITY` tuned from eval dataset (data-driven, not arbitrary)
- [ ] RAG eval: Precision@5 ≥ 0.80, Recall@5 ≥ 0.85, MRR reported
- [ ] All 155+ Phase 02/03 tests continue to pass
- [ ] `ruff check` PASS, `mypy` PASS

---

## Completion Record

- **Planned:** 2026-07-14 (revision 4 — final)
- **Started:** TBD
- **04A Completed:** TBD
- **04B Completed:** TBD
