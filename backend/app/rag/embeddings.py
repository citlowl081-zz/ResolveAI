"""EmbeddingProvider ABC and factory — Phase 04A Batch 2.

Mirrors the ``ModelProvider`` pattern in ``app/llm/provider.py`` but for
embedding generation rather than chat completion.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.config.settings import settings


class EmbeddingProvider(ABC):
    """Async embedding provider with a fixed, declared dimension.

    Every implementation (mock, OpenAI-compatible, etc.) must provide
    ``embed``, ``embed_query``, ``dimension``, and ``provider_name``.
    """

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Returns one vector per input text in the same order.
        """
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text.

        Equivalent to ``(await embed([text]))[0]`` but may be optimised.
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension. Must match the database column (1536)."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable identifier for logs and traces."""
        ...


# ──────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────


def build_embedding_provider(provider: str | None = None) -> EmbeddingProvider:
    """Build an ``EmbeddingProvider`` from application settings.

    Parameters
    ----------
    provider:
        Override ``EMBEDDING_PROVIDER``.  When ``None`` the value from
        ``settings`` is used.

    Raises
    ------
    ValueError:
        If ``EMBEDDING_PROVIDER`` is unknown.
    SystemExit:
        If ``EMBEDDING_DIMENSION`` is not 1536.
    ValueError:
        If the provider requires an API key and none is configured.
    """
    p = provider or settings.embedding_provider

    if settings.embedding_dimension != 1536:
        raise SystemExit(
            f"EMBEDDING_DIMENSION is {settings.embedding_dimension}, "
            f"but the database column is vector(1536). "
            f"Set EMBEDDING_DIMENSION=1536."
        )

    if p == "mock":
        from app.rag.mock_embeddings import MockEmbeddingProvider

        return MockEmbeddingProvider(dimension=settings.embedding_dimension)

    if p == "openai":
        if not settings.embedding_api_key:
            raise ValueError(
                "EMBEDDING_PROVIDER=openai requires EMBEDDING_API_KEY to be set"
            )
        from app.rag.openai_embeddings import OpenAICompatibleEmbeddingProvider

        return OpenAICompatibleEmbeddingProvider(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            timeout=settings.embedding_timeout_seconds,
            max_retries=settings.embedding_max_retries,
        )

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER '{p}'.  Expected 'mock' or 'openai'."
    )
