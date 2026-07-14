"""Unit tests for MockEmbeddingProvider — no external API calls."""

import math

import pytest

from app.rag.mock_embeddings import (
    MockEmbeddingProvider,
    _bigram_hash_vector,
    _extract_bigrams,
    _normalize,
)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class TestNormalize:
    def test_fullwidth_to_halfwidth(self) -> None:
        fullwidth = "ＡＢＣ"  # ＡＢＣ
        result = _normalize(fullwidth)
        assert result == "abc"

    def test_lowercase(self) -> None:
        assert _normalize("Hello World") == "hello world"

    def test_collapse_whitespace(self) -> None:
        assert _normalize("hello   \n  world\t!") == "hello world !"

    def test_strip(self) -> None:
        assert _normalize("  hello  ") == "hello"

    def test_control_char_removal(self) -> None:
        assert _normalize("hello\x00world") == "helloworld"


class TestExtractBigrams:
    def test_chinese(self) -> None:
        bg = _extract_bigrams("订单")
        assert bg == ["^订", "订单", "单$"]

    def test_single_char(self) -> None:
        bg = _extract_bigrams("A")
        assert bg == ["^A", "A$"]

    def test_empty(self) -> None:
        assert _extract_bigrams("") == []

    def test_numbers(self) -> None:
        bg = _extract_bigrams("100")
        assert "^1" in bg
        assert "0$" in bg


class TestBigramHashVector:
    def test_dimension(self) -> None:
        v = _bigram_hash_vector("hello world", 1536)
        assert len(v) == 1536

    def test_empty_text_zero_vector(self) -> None:
        v = _bigram_hash_vector("", 1536)
        assert v == [0.0] * 1536

    def test_whitespace_only_zero_vector(self) -> None:
        v = _bigram_hash_vector("   \n  ", 1536)
        assert v == [0.0] * 1536

    def test_non_zero_for_real_text(self) -> None:
        v = _bigram_hash_vector("hello", 1536)
        assert any(x != 0.0 for x in v)

    def test_deterministic(self) -> None:
        v1 = _bigram_hash_vector("你好世界", 1536)
        v2 = _bigram_hash_vector("你好世界", 1536)
        assert v1 == v2

    def test_l2_norm_close_to_one(self) -> None:
        v = _bigram_hash_vector("some meaningful text here", 1536)
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-9

    def test_fullwidth_normalized_same_as_halfwidth(self) -> None:
        # Fullwidth "ＰＯＬ" normalizes to "pol"
        v_full = _bigram_hash_vector("ＰＯＬ", 1536)
        v_half = _bigram_hash_vector("POL", 1536)
        assert v_full == v_half

    def test_single_char_has_feature(self) -> None:
        v = _bigram_hash_vector("A", 1536)
        assert any(x != 0.0 for x in v)


class TestMockEmbeddingProvider:
    @pytest.mark.asyncio
    async def test_embed_returns_correct_count(self) -> None:
        p = MockEmbeddingProvider()
        results = await p.embed(["a", "b", "c"])
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_embed_query_dimension(self) -> None:
        p = MockEmbeddingProvider()
        v = await p.embed_query("test")
        assert len(v) == 1536

    @pytest.mark.asyncio
    async def test_similar_texts_higher_score(self) -> None:
        p = MockEmbeddingProvider()
        a = await p.embed_query("订单未发货退款")
        b = await p.embed_query("订单未发货申请退款")
        c = await p.embed_query("物流查询规则")
        assert _cosine(a, b) > _cosine(a, c)

    @pytest.mark.asyncio
    async def test_mixed_chinese_english(self) -> None:
        p = MockEmbeddingProvider()
        v = await p.embed_query("订单ABC退款")
        assert len(v) == 1536
        assert any(x != 0.0 for x in v)

    @pytest.mark.asyncio
    async def test_dimension_property(self) -> None:
        p = MockEmbeddingProvider(dimension=1536)
        assert p.dimension == 1536

    @pytest.mark.asyncio
    async def test_provider_name(self) -> None:
        p = MockEmbeddingProvider()
        assert p.provider_name == "mock"
