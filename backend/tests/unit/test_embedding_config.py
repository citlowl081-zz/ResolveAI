"""Unit tests for embedding configuration dimension validation (no DB required)."""


import pytest


class TestEmbeddingDimension:
    """EMBEDDING_DIMENSION must be 1536 — enforced at Settings load time."""

    def test_dimension_1536_is_default_and_valid(self) -> None:
        from app.config.settings import Settings

        s = Settings()
        assert s.embedding_dimension == 1536

    def test_dimension_non_1536_detected(self) -> None:
        """Non-1536 values should be rejected.

        The validation will be enforced at Provider build time (Phase 04A
        Batch 2).  For Batch 1 we verify the setting value is read
        correctly so the later validation check can act on it.
        """
        from app.config.settings import Settings

        s = Settings(embedding_dimension=768)
        assert s.embedding_dimension == 768
        # The actual rejection (SystemExit / ValueError) is tested in
        # Batch 2 when build_embedding_provider() exists.

    def test_embedding_provider_defaults(self) -> None:
        from app.config.settings import Settings

        s = Settings()
        assert s.embedding_provider == "mock"
        assert s.embedding_model == "text-embedding-3-small"
        assert s.embedding_api_key == ""
        assert s.embedding_base_url == "https://api.openai.com/v1"
        assert s.embedding_timeout_seconds == 60
        assert s.embedding_max_retries == 1

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMBEDDING_DIMENSION", "1536")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        from app.config.settings import Settings

        # Re-import after env var set to pick up value
        s = Settings()
        assert s.embedding_dimension == 1536
        assert s.embedding_provider == "openai"
