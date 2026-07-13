"""Unit tests for application configuration."""

import os


def test_settings_defaults() -> None:
    """Settings load with expected default values."""
    from app.config.settings import Settings

    s = Settings()
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
