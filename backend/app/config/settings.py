"""Application configuration via Pydantic Settings.

Reads from environment variables with prefix support.
"""

from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "ResolveAI"
    app_version: str = "1.0.1"
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

    # ---- LLM (Phase 03+) ----
    llm_provider: str = "mock"
    llm_model: str = "qwen3.7-plus"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.3
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 1

    # ---- Embedding (Phase 04+) ----
    embedding_provider: str = "mock"
    """``"mock"`` (deterministic test vectors) or ``"openai"`` (OpenAI-compatible /v1/embeddings)."""

    embedding_model: str = "text-embedding-3-small"
    """Model name sent in the /v1/embeddings request body."""

    embedding_api_key: str = ""
    """API key sent as ``Authorization: Bearer <key>``.  Empty for mock."""

    embedding_base_url: str = "https://api.openai.com/v1"
    """Base URL for the OpenAI-compatible embeddings endpoint (``/embeddings`` appended)."""

    embedding_dimension: int = 1536
    """**MUST be 1536.**  The database column is ``vector(1536)`` — any other value causes
    a start-up failure.  This field acts as a configuration validation check, not a
    mechanism to change the database dimension."""

    embedding_timeout_seconds: int = 60
    embedding_max_retries: int = 1

    # ---- RAG (Phase 04+) ----
    rag_top_k: int = 5
    """Default number of policy results returned by vector search."""

    rag_min_similarity: float | None = None
    """Minimum cosine similarity threshold.  ``None`` = return all results.
    Tune from eval data in Phase 04B."""

    # ---- JWT (Phase 02+) ----
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ---- Agent (Phase 03+) ----
    agent_context_token_budget: int = 8000
    agent_max_messages_per_session: int = 100
    agent_max_tools_per_turn: int = 5
    agent_max_loops_per_turn: int = 3
    agent_tool_timeout_seconds: int = 30
    agent_turn_expiry_seconds: int = 90
    agent_pending_action_expiry_seconds: int = 300
    agent_max_concurrent_sessions: int = 10

    # ---- Rate Limiting ----
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> Self:
        """Fail startup explicitly for unsupported or incomplete real providers."""
        provider = self.llm_provider.strip().lower()
        if provider not in {"mock", "anthropic", "openai_compatible"}:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
        if provider == "anthropic" and not self.llm_api_key:
            raise ValueError("Anthropic provider configuration is incomplete")
        if provider == "openai_compatible" and (
            not self.llm_api_key or not self.llm_base_url
        ):
            raise ValueError(
                "OpenAI-compatible provider configuration is incomplete"
            )
        return self


settings = Settings()
