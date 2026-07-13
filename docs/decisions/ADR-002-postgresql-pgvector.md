# ADR-002: PostgreSQL + pgvector as Database and Vector Store

## Status
Accepted

## Context
We need a database for business data (users, orders, tickets, etc.) and a vector store for RAG (policy document embeddings). We must decide whether to use two separate systems or one unified system.

## Decision
Use PostgreSQL 16 with the pgvector extension as the single database for both relational data and vector embeddings.

## Alternatives Considered

### PostgreSQL + Separate Vector DB (Pinecone, Weaviate, Milvus)
- **Pros:** Purpose-built for vector search, potentially better performance at scale.
- **Cons:** Two databases to manage, deploy, back up, and monitor. Increased operational complexity. For a demo project with <1000 policy documents, pgvector's performance is more than sufficient.

### PostgreSQL Only (no pgvector, custom embedding logic)
- **Pros:** Fewest dependencies.
- **Cons:** Would need to implement vector similarity search manually or use an inferior keyword-based approach.

### Chroma / FAISS (embedded)
- **Pros:** Simple to set up, no external service.
- **Cons:** Another dependency. Persistence and backup are less mature. Doesn't integrate with SQL queries.

## Why pgvector?
1. **Single database:** One Docker container, one connection string, one backup strategy.
2. **SQL + Vector:** Can join vector search results with metadata tables in a single query.
3. **Sufficient performance:** pgvector with IVFFlat indexes handles our scale (<1000 documents) easily with sub-100ms queries.
4. **Mature:** pgvector is well-maintained, supports IVF and HNSW indexes, cosine/L2/inner product distances.
5. **Alembic compatible:** Schema migrations for vector columns work just like regular columns.

## Consequences

### Easier
- Single database to deploy and manage.
- Vector search can be combined with SQL filters in one query.
- Backup/restore is a single PostgreSQL operation.
- One less service in Docker Compose.

### More Difficult
- If we ever need >1M documents, may need to migrate to a dedicated vector DB.
- pgvector's HNSW index creation is slower than some dedicated solutions (not relevant at our scale).

## References
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvector Documentation](https://github.com/pgvector/pgvector#readme)
