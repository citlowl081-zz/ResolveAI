"""Application configuration via Pydantic Settings.

Reads from environment variables with prefix support.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "ResolveAI"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"

    # ---- Database ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "resolveai"
    postgres_user: str = "resolveai"
    postgres_password: str = "resolveai-dev"
    database_url: str | None = None

    @property
    def resolved_database_url(self) -> str:
        """Return DATABASE_URL if explicitly set, otherwise build from components."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    test_database_url: str | None = None

    # ---- CORS ----
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ---- LLM (unused in Phase 01, needed by Phase 03+) ----
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-5-20251001"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.anthropic.com"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1
    llm_timeout_seconds: int = 60

    # ---- Embedding (unused in Phase 01, needed by Phase 04+) ----
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_dimension: int = 1536

    # ---- JWT (unused in Phase 01, needed by Phase 02+) ----
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ---- Agent (unused in Phase 01, needed by Phase 03+) ----
    agent_max_retries: int = 2
    agent_tool_timeout_seconds: int = 30
    agent_session_ttl_minutes: int = 60
    agent_high_risk_amount_threshold: float = 1000.00
    agent_max_concurrent_sessions: int = 10

    # ---- Rate Limiting ----
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60


settings = Settings()
