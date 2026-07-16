"""Ingest all 14 policy documents into the RAG knowledge base.
Idempotent — skips documents whose content_hash hasn't changed.
Runs once at container startup after migrations and seed.
"""

import asyncio
from pathlib import Path

from app.database.session import _get_session_factory
from app.rag.embeddings import build_embedding_provider
from app.rag.ingestion import PolicyIngestionService

POLICIES_DIR = Path("/app/data/policies")
FALLBACK_DIR = Path(__file__).resolve().parents[2] / "data" / "policies"


async def main() -> None:
    policies_dir = POLICIES_DIR if POLICIES_DIR.exists() else FALLBACK_DIR
    if not policies_dir.exists():
        print(f"IngestPolicies: directory not found at {policies_dir}, skipping.")
        return

    factory = _get_session_factory()
    provider = build_embedding_provider()
    ingester = PolicyIngestionService(
        session_factory=factory,
        embedding_provider=provider,
        policies_dir=policies_dir,
    )
    results = await ingester.ingest_all(activate=True)
    total = len(results)
    print(f"IngestPolicies: {total} policy files processed")


if __name__ == "__main__":
    asyncio.run(main())
