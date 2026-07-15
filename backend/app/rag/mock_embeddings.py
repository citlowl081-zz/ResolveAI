"""MockEmbeddingProvider — deterministic Chinese-friendly embedding vectors.

Uses character bigram feature hashing with BLAKE2b for stable,
reproducible, similarity-preserving vectors.  Zero external API calls.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

from app.rag.embeddings import EmbeddingProvider

# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Normalise *text*: NFKC, lowercase, collapse whitespace, strip.

    This ensures that semantically identical inputs (fullwidth vs
    halfwidth, extra spaces, mixed case) produce the same bigrams and
    therefore the same embedding.
    """
    t = unicodedata.normalize("NFKC", text)
    t = t.lower()
    t = re.sub(r"\s+", " ", t)
    t = t.strip()
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", t)
    return t


# ---------------------------------------------------------------------------
# Bigram extraction
# ---------------------------------------------------------------------------


def _extract_bigrams(text: str) -> list[str]:
    """Extract character bigrams with start/end sentinels.

    ``"订单"`` → ``["^订", "订单", "单$"]``

    Single-character input (after normalisation) still produces at least
    two bigrams thanks to the sentinels.
    """
    chars = list(text)
    if not chars:
        return []
    bigrams = [f"^{chars[0]}"]
    for i in range(len(chars) - 1):
        bigrams.append(f"{chars[i]}{chars[i + 1]}")
    bigrams.append(f"{chars[-1]}$")
    return bigrams


def _extract_unigrams(text: str) -> list[str]:
    """Extract single-character unigrams with position-weighted sentinels.

    Adds a position-independent unigram for each unique character, plus
    frequency-weighted duplicates for repeated chars to amplify common
    characters.
    """
    chars = list(text)
    if not chars:
        return []
    return [f"_{c}" for c in chars]


# ---------------------------------------------------------------------------
# BLAKE2b-based feature hashing
# ---------------------------------------------------------------------------


def _bigram_hash_vector(text: str, dimension: int) -> list[float]:
    """Return a deterministic ``dimension``-dimensional vector for *text*.

    Algorithm:
    1. Normalise (NFKC + lowercase + whitespace collapse)
    2. Extract character bigrams with sentinels
    3. For each bigram, hash with BLAKE2b → 64-bit index
    4. Increment the term-frequency count at that index
    5. L2-normalise the final vector

    Empty / whitespace-only text returns a zero vector.
    """
    normalized = _normalize(text)
    bigrams = _extract_bigrams(normalized)
    unigrams = _extract_unigrams(normalized)

    vec = [0.0] * dimension
    if not bigrams and not unigrams:
        return vec  # zero vector for empty text

    # Bigrams: weight 2.0 for structural context
    for bg in bigrams:
        digest = hashlib.blake2b(bg.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest, "big") % dimension
        vec[idx] += 2.0

    # Unigrams: weight 0.5 for keyword presence
    for ug in unigrams:
        digest = hashlib.blake2b(ug.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest, "big") % dimension
        vec[idx] += 0.5

    # L2-normalise
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0.0:
        vec = [v / norm for v in vec]
    return vec


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class MockEmbeddingProvider(EmbeddingProvider):
    """Embedding provider that returns deterministic bigram-hash vectors.

    Parameters
    ----------
    dimension:
        Output vector dimension.  Must match the database column (1536).
    """

    def __init__(self, dimension: int = 1536) -> None:
        self._dimension = dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Each text is processed independently — no batching optimisation
        is needed for mock embeddings.
        """
        return [_bigram_hash_vector(t, self._dimension) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        return _bigram_hash_vector(text, self._dimension)

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def provider_name(self) -> str:
        return "mock"
