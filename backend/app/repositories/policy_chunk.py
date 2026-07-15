"""PolicyChunkRepository — bulk save + pgvector exact cosine search."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy_chunk import PolicyChunk
from app.repositories.base import BaseRepository


class PolicyChunkRepository(BaseRepository):
    """Repository for ``PolicyChunk`` rows and pgvector vector search.

    Write methods are declared for future use (Batch 4 ingestion) but
    are not called during Batch 3.
    """

    model = PolicyChunk

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ── Write (for Batch 4) ──────────────────────────────────────────

    async def bulk_save(self, chunks: list[PolicyChunk]) -> list[PolicyChunk]:
        """Persist a batch of chunk rows.  Caller must commit."""
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def delete_by_document_id(self, document_id: uuid.UUID) -> None:
        """Delete all chunks for *document_id* (used before re-embed)."""
        result = await self.session.execute(
            select(PolicyChunk).where(
                PolicyChunk.policy_document_id == document_id
            )
        )
        for row in result.scalars().all():
            await self.session.delete(row)
        await self.session.flush()

    # ── Vector search ────────────────────────────────────────────────

    async def search_similar(
        self,
        query_vector: list[float],
        top_k: int = 5,
        category: str | None = None,
        min_similarity: float | None = None,
    ) -> list[dict]:
        """Exact cosine similarity search via pgvector ``<=>``.

        Parameters
        ----------
        query_vector:
            The query embedding (must be the same dimension as the
            ``vector(1536)`` column).
        top_k:
            Maximum number of results to return (after dedup per
            policy_key).
        category:
            Optional ``policy_category`` filter applied in SQL.
        min_similarity:
            Optional minimum cosine similarity.  ``None`` = return all.

        Returns
        -------
        list[dict]
            Each dict contains ``policy_key``, ``version``, ``title``,
            ``category``, ``content_summary``, ``snippet``,
            ``chunk_index``, and ``similarity_score``.  No internal
            UUIDs, ``content_hash``, or full ``content`` are returned.
        """
        # Build the query vector string for PostgreSQL.
        # Use f-string interpolation for the vector (safe — list of floats)
        # and bind params for user-controlled values (category, max_candidates).
        vec_str = f"[{','.join(str(v) for v in query_vector)}]"

        sql = text(f"""
            SELECT
                pd.policy_key,
                pd.version,
                pd.title,
                pd.category::text,
                pd.content_summary,
                pc.content AS snippet,
                pc.chunk_index,
                1 - (pc.embedding <=> '{vec_str}'::vector) AS similarity_score
            FROM policy_chunks pc
            JOIN policy_documents pd ON pc.policy_document_id = pd.id
            WHERE pd.status = 'ACTIVE'
              AND pd.effective_date <= CURRENT_DATE
              AND (pd.expiration_date IS NULL OR pd.expiration_date >= CURRENT_DATE)
              AND (:category IS NULL OR pd.category::text = :category)
            ORDER BY pc.embedding <=> '{vec_str}'::vector
            LIMIT :max_candidates
        """)

        result = await self.session.execute(
            sql.bindparams(
                sa.bindparam("category", value=category, type_=sa.String()),
                sa.bindparam("max_candidates", value=top_k * 3, type_=sa.Integer()),
            ),
        )

        rows = result.mappings().all()

        # ── Post-processing in Python ────────────────────────────────
        # 1. min_similarity filter
        if min_similarity is not None:
            rows = [r for r in rows if r["similarity_score"] >= min_similarity]

        # 2. Dedup: keep highest-scoring chunk per policy_key
        best: dict[str, dict] = {}
        for r in rows:
            pk = r["policy_key"]
            if pk not in best or r["similarity_score"] > best[pk]["similarity_score"]:
                best[pk] = dict(r)

        # 3. Sort by score descending, take top_k
        sorted_results = sorted(
            best.values(), key=lambda d: d["similarity_score"], reverse=True
        )
        return sorted_results[:top_k]
