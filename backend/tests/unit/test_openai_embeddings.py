"""Unit tests for OpenAICompatibleEmbeddingProvider — mock HTTP, no real API."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.rag.openai_embeddings import OpenAICompatibleEmbeddingProvider


def _make_mock_response(
    status: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = json_data or {"data": []}
    resp.text = text
    resp.read.return_value = b""
    resp.raise_for_status.side_effect = (
        httpx.HTTPStatusError("err", request=MagicMock(), response=resp)
        if status >= 400
        else None
    )
    return resp


def _make_provider(**overrides: object) -> OpenAICompatibleEmbeddingProvider:
    kwargs: dict = {
        "api_key": "sk-test",
        "base_url": "https://api.openai.com/v1",
        "model": "text-embedding-3-small",
        "dimension": 1536,
        "timeout": 10,
        "max_retries": 0,
    }
    kwargs.update({k: v for k, v in overrides.items() if v is not ...})
    return OpenAICompatibleEmbeddingProvider(**kwargs)


class TestSuccess:
    @pytest.mark.asyncio
    async def test_successful_batch(self) -> None:
        provider = _make_provider()
        mock_resp = _make_mock_response(json_data={
            "data": [
                {"index": 0, "embedding": [0.1] * 1536},
                {"index": 1, "embedding": [0.2] * 1536},
            ],
        })
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            results = await provider.embed(["text a", "text b"])
            assert len(results) == 2
            assert len(results[0]) == 1536

    @pytest.mark.asyncio
    async def test_response_sorted_by_index(self) -> None:
        provider = _make_provider()
        mock_resp = _make_mock_response(json_data={
            "data": [
                {"index": 1, "embedding": [0.2] * 1536},
                {"index": 0, "embedding": [0.1] * 1536},
            ],
        })
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            results = await provider.embed(["a", "b"])
            assert results[0][0] == 0.1
            assert results[1][0] == 0.2


class TestEmptyInput:
    @pytest.mark.asyncio
    async def test_empty_texts_raises(self) -> None:
        provider = _make_provider()
        with pytest.raises(ValueError, match="not be empty"):
            await provider.embed([])


class TestRetry:
    @pytest.mark.asyncio
    async def test_timeout_retries(self) -> None:
        provider = _make_provider(max_retries=1)
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                httpx.TimeoutException("timeout"),
                _make_mock_response(json_data={
                    "data": [{"index": 0, "embedding": [0.1] * 1536}],
                }),
            ]
            results = await provider.embed(["a"])
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_429_retries(self) -> None:
        provider = _make_provider(max_retries=1)
        resp_429 = _make_mock_response(status=429, json_data={"error": "rate limited"})
        resp_ok = _make_mock_response(json_data={
            "data": [{"index": 0, "embedding": [0.1] * 1536}],
        })
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [resp_429.raise_for_status.side_effect, resp_ok]
            results = await provider.embed(["a"])
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_5xx_retries(self) -> None:
        provider = _make_provider(max_retries=1)
        resp_500 = _make_mock_response(status=500, json_data={"error": "server error"})
        resp_ok = _make_mock_response(json_data={
            "data": [{"index": 0, "embedding": [0.1] * 1536}],
        })
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [resp_500.raise_for_status.side_effect, resp_ok]
            results = await provider.embed(["a"])
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_400_no_retry(self) -> None:
        provider = _make_provider(max_retries=1)
        resp_400 = _make_mock_response(status=400, json_data={"error": "bad request"})
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = resp_400.raise_for_status.side_effect
            with pytest.raises(httpx.HTTPStatusError):
                await provider.embed(["a"])
            assert mock_post.call_count == 1  # no retry


class TestMalformedResponse:
    @pytest.mark.asyncio
    async def test_missing_data(self) -> None:
        provider = _make_provider()
        mock_resp = _make_mock_response(json_data={"object": "list"})
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(RuntimeError, match="missing 'data'"):
                await provider.embed(["a"])

    @pytest.mark.asyncio
    async def test_wrong_count(self) -> None:
        provider = _make_provider()
        mock_resp = _make_mock_response(json_data={
            "data": [{"index": 0, "embedding": [0.1] * 1536}],
        })
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(RuntimeError, match="expected 2"):
                await provider.embed(["a", "b"])

    @pytest.mark.asyncio
    async def test_wrong_dimension(self) -> None:
        provider = _make_provider()
        mock_resp = _make_mock_response(json_data={
            "data": [{"index": 0, "embedding": [0.1] * 768}],
        })
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(RuntimeError, match="dimension 768"):
                await provider.embed(["a"])


class TestConstructor:
    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            OpenAICompatibleEmbeddingProvider(
                api_key="", base_url="https://api.com", model="m", dimension=1536,
            )

    @pytest.mark.asyncio
    async def test_provider_name(self) -> None:
        provider = _make_provider()
        assert provider.provider_name == "openai"

    @pytest.mark.asyncio
    async def test_dimension_property(self) -> None:
        provider = _make_provider()
        assert provider.dimension == 1536

    @pytest.mark.asyncio
    async def test_aclose(self) -> None:
        provider = _make_provider()
        await provider.aclose()
        # Should be idempotent
        await provider.aclose()
