"""RAG (Retrieval-Augmented Generation) module — Phase 04.

Batch 1 provides policy_key validation.  Embedding providers, chunking,
ingestion, and retrieval arrive in later batches.
"""

from app.rag.validation import (
    POLICY_KEY_PREFIXES,
    POLICY_KEY_RE,
    validate_policy_key,
    validate_policy_key_and_category,
)

__all__ = [
    "POLICY_KEY_RE",
    "POLICY_KEY_PREFIXES",
    "validate_policy_key",
    "validate_policy_key_and_category",
]
