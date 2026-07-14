"""RAG (Retrieval-Augmented Generation) module — Phase 04.

Batch 1: policy_key validation.
Batch 2: embedding providers, chunking, content hashing.
"""

from app.rag.chunking import chunk_text
from app.rag.content_hash import compute_content_hash
from app.rag.embeddings import EmbeddingProvider, build_embedding_provider
from app.rag.mock_embeddings import MockEmbeddingProvider
from app.rag.openai_embeddings import OpenAICompatibleEmbeddingProvider
from app.rag.validation import (
    POLICY_KEY_PREFIXES,
    POLICY_KEY_RE,
    validate_policy_key,
    validate_policy_key_and_category,
)

__all__ = [
    # validation (Batch 1)
    "POLICY_KEY_RE",
    "POLICY_KEY_PREFIXES",
    "validate_policy_key",
    "validate_policy_key_and_category",
    # embeddings (Batch 2)
    "EmbeddingProvider",
    "MockEmbeddingProvider",
    "OpenAICompatibleEmbeddingProvider",
    "build_embedding_provider",
    # chunking (Batch 2)
    "chunk_text",
    # content hash (Batch 2)
    "compute_content_hash",
]
