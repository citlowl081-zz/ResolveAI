"""OpenAICompatibleEmbeddingProvider — httpx-based /v1/embeddings client.

No ``openai`` SDK dependency.  Works with any service that speaks the
standard OpenAI ``/v1/embeddings`` request and response format.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.rag.embeddings import EmbeddingProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


def _is_retryable(exc: Exception) -> bool:
    """Return ``True`` for transient errors worth retrying."""
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, httpx.RemoteProtocolError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUSES
    return False


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible embeddings via ``/v1/embeddings``.

    Parameters
    ----------
    api_key:
        Sent as ``Authorization: Bearer <key>``.
    base_url:
        Base URL; ``/embeddings`` is appended.  Must include the
        scheme and path prefix (e.g. ``"https://api.openai.com/v1"``).
    model:
        Model name in the request body.
    dimension:
        Expected output dimension (must be 1536).
    timeout:
        Per-request timeout in seconds.
    max_retries:
        Maximum automatic retries for transient errors.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        dimension: int,
        timeout: int = 60,
        max_retries: int = 1,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required for OpenAICompatibleEmbeddingProvider")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimension = dimension
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # EmbeddingProvider interface
    # ------------------------------------------------------------------

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Raises
        ------
        ValueError:
            If *texts* is empty.
        RuntimeError:
            If the API response is malformed (wrong count, wrong
            dimension, missing fields).
        httpx.HTTPError:
            For non-retryable HTTP errors (4xx other than 429).
        httpx.TimeoutException:
            If all retries are exhausted.
        """
        if not texts:
            raise ValueError("texts must not be empty")

        return await self._call_with_retry(texts)

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        results = await self.embed([text])
        return results[0]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def provider_name(self) -> str:
        return "openai"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _call_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Call the API with bounded retries on transient errors."""
        client = self._get_client()
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return await self._call(client, texts)
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries and _is_retryable(exc):
                    # Simple back-off: 1s, 2s, 4s, …
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        # Should be unreachable — the loop either returns or raises
        assert last_exc is not None
        raise last_exc

    async def _call(
        self, client: httpx.AsyncClient, texts: list[str],
    ) -> list[list[float]]:
        """Single API call — no retry."""
        url = f"{self._base_url}/embeddings"
        body: dict[str, Any] = {
            "model": self._model,
            "input": texts,
        }

        response = await client.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )

        # Non-2xx → raise so the retry logic can inspect it
        if response.status_code >= 400:
            response.read()  # consume body for the exception
            response.raise_for_status()

        data: dict[str, Any] = response.json()

        # ── Validate response shape ────────────────────────────────
        if "data" not in data or not isinstance(data["data"], list):
            raise RuntimeError("OpenAI embeddings response missing 'data' array")

        items: list[dict[str, Any]] = data["data"]
        if len(items) != len(texts):
            raise RuntimeError(
                f"OpenAI embeddings returned {len(items)} vectors, "
                f"expected {len(texts)}"
            )

        # Sort by index (they may arrive out of order)
        items.sort(key=lambda d: d.get("index", 0))

        vectors: list[list[float]] = []
        for i, item in enumerate(items):
            emb = item.get("embedding")
            if not isinstance(emb, list):
                raise RuntimeError(
                    f"OpenAI embeddings item {i} missing 'embedding' list"
                )
            if len(emb) != self._dimension:
                raise RuntimeError(
                    f"OpenAI embeddings item {i} has dimension {len(emb)}, "
                    f"expected {self._dimension}"
                )
            vectors.append(list(emb))

        # Final size check after index-sort (belt-and-suspenders)
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"OpenAI embeddings produced {len(vectors)} usable vectors "
                f"after validation, expected {len(texts)}"
            )

        return vectors

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy-construct the httpx client (no network call on construction)."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def aclose(self) -> None:
        """Close the underlying httpx client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
