"""Unit tests for application configuration."""

import os

import pytest


def test_settings_defaults() -> None:
    """Settings load with expected default values."""
    from app.config.settings import Settings

    s = Settings.model_construct()
    assert s.app_name == "ResolveAI"
    assert s.app_version == "0.1.0"
    assert s.app_env == "development"
    assert s.debug is True
    assert s.postgres_host == "localhost"
    assert s.postgres_port == 5432


def test_resolved_database_url_from_components() -> None:
    """DATABASE_URL is built from components when not explicitly set."""
    from app.config.settings import Settings

    s = Settings(database_url=None)
    url = s.resolved_database_url
    assert url.startswith("postgresql+asyncpg://")
    assert "resolveai" in url
    assert "5432" in url


def test_resolved_database_url_explicit() -> None:
    """Explicit DATABASE_URL takes precedence over components."""
    from app.config.settings import Settings

    explicit = "postgresql+asyncpg://custom:pass@custom-host:9999/custom-db"
    s = Settings(database_url=explicit)
    assert s.resolved_database_url == explicit


def test_cors_origin_list_parsing() -> None:
    """CORS origins string is split into a list."""
    from app.config.settings import Settings

    s = Settings(cors_origins="http://a:3000, http://b:3001")
    assert s.cors_origin_list == ["http://a:3000", "http://b:3001"]


def test_env_override() -> None:
    """Environment variables override defaults."""
    os.environ["APP_ENV"] = "production"
    try:
        from app.config.settings import Settings

        s = Settings()
        assert s.app_env == "production"
    finally:
        del os.environ["APP_ENV"]


def test_openai_compatible_settings_require_key_and_base_url() -> None:
    """Incomplete real-provider configuration fails explicitly."""
    from pydantic import ValidationError

    from app.config.settings import Settings

    with pytest.raises(ValidationError, match="configuration is incomplete"):
        Settings(
            debug=False,
            llm_provider="openai_compatible",
            llm_api_key="",
            llm_base_url="",
        )


def test_settings_ignore_unrelated_env_file_fields() -> None:
    """A shared root .env may contain frontend and seed-only variables."""
    from app.config.settings import Settings

    config = Settings.model_validate({
        "llm_provider": "mock",
        "next_public_api_base_url": "http://localhost:8000/api/v1",
    })

    assert config.llm_provider == "mock"
