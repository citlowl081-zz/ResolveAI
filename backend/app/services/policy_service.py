"""PolicyService — retrieval and (future) lifecycle management.

Batch 3 implements ``search()`` with strict embedding-transaction
boundary safety.  Write operations arrive in Batch 4.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.rag.embeddings import EmbeddingProvider
from app.repositories.policy_chunk import PolicyChunkRepository


class PolicyService:
    """Service for policy retrieval with pgvector search.

    Parameters
    ----------
    session_factory:
        An ``async_sessionmaker`` used to create short-lived DB
        sessions during search.  Sessions are created AFTER the
        embedding call and closed before returning.
    embedding_provider:
        The ``EmbeddingProvider`` used to embed the user's query.
        Must be pre-built by the factory.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._session_factory = session_factory
        self._embedding = embedding_provider

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_similarity: float | None = None,
    ) -> list[dict]:
        """Search for policies relevant to *query*.

        **Transaction boundary contract (hard constraint):**

        1. Call ``embed_query(query)`` — **NO DB session open**.
        2. Open a short-lived DB session.
        3. Execute the vector search SQL.
        4. Close the session.
        5. Return results.

        No database session, transaction, or row lock is held during
        the embedding API call.

        Returns
        -------
        list[dict]
            Each dict has ``policy_key``, ``version``, ``title``,
            ``category``, ``content_summary``, ``snippet``,
            ``chunk_index``, ``similarity_score``.  Empty list when
            no matching policies are found.
        """
        # ── Phase 1: Embed query (NO DB connection) ──────────────────
        if self._embedding.dimension != 1536:
            raise RuntimeError(
                f"Embedding dimension mismatch: provider returns "
                f"{self._embedding.dimension}, expected 1536"
            )
        query_vector = await self._embedding.embed_query(query)

        # ── Phase 2: Vector search (short DB transaction) ────────────
        async with self._session_factory() as session:
            repo = PolicyChunkRepository(session)
            results = await repo.search_similar(
                query_vector=query_vector,
                top_k=top_k,
                category=category,
                min_similarity=min_similarity,
            )

        # Session is closed here — results are detached dicts
        return results
