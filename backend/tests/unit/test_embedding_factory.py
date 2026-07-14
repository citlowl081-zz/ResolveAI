"""Unit tests for build_embedding_provider factory."""

from unittest.mock import patch

import pytest

from app.rag.embeddings import build_embedding_provider
from app.rag.mock_embeddings import MockEmbeddingProvider
from app.rag.openai_embeddings import OpenAICompatibleEmbeddingProvider


class TestFactoryMock:
    def test_mock_created_with_defaults(self) -> None:
        p = build_embedding_provider("mock")
        assert isinstance(p, MockEmbeddingProvider)
        assert p.dimension == 1536

    def test_mock_ignores_api_key(self) -> None:
        """Mock provider should not require or validate an API key."""
        p = build_embedding_provider("mock")
        assert isinstance(p, MockEmbeddingProvider)


class TestFactoryOpenAI:
    def test_openai_created(self) -> None:
        """OpenAI provider created when API key is configured."""
        with patch("app.rag.embeddings.settings.embedding_api_key", "sk-test"):
            p = build_embedding_provider("openai")
        assert isinstance(p, OpenAICompatibleEmbeddingProvider)
        assert p.dimension == 1536

    def test_openai_missing_key(self) -> None:
        """OpenAI provider raises when no API key is configured."""
        with (
            patch("app.rag.embeddings.settings.embedding_api_key", ""),
            pytest.raises(ValueError, match="EMBEDDING_API_KEY"),
        ):
            build_embedding_provider("openai")


class TestFactoryErrors:
    def test_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unknown EMBEDDING_PROVIDER"):
            build_embedding_provider("unknown")

    def test_dimension_not_1536(self) -> None:
        with (
            patch("app.rag.embeddings.settings.embedding_dimension", 768),
            pytest.raises(SystemExit, match="EMBEDDING_DIMENSION"),
        ):
            build_embedding_provider("mock")
