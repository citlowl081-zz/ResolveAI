"""Construct the configured vendor-neutral model provider."""

from __future__ import annotations

from app.config.settings import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.mock_provider import MockProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider
from app.llm.provider import ModelProvider


def build_model_provider(config: Settings) -> ModelProvider:
    """Build a provider or fail explicitly when real configuration is incomplete."""
    provider = config.llm_provider.strip().lower()
    if provider == "mock":
        return MockProvider()
    if provider == "anthropic":
        if not config.llm_api_key:
            raise RuntimeError("Anthropic provider configuration is incomplete")
        return AnthropicProvider(
            api_key=config.llm_api_key,
            default_model=config.llm_model,
            timeout=config.llm_timeout_seconds,
            max_retries=config.llm_max_retries,
            base_url=config.llm_base_url or None,
        )
    if provider == "openai_compatible":
        if not config.llm_api_key or not config.llm_base_url:
            raise RuntimeError(
                "OpenAI-compatible provider configuration is incomplete"
            )
        return OpenAICompatibleProvider(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            default_model=config.llm_model,
            timeout=config.llm_timeout_seconds,
            max_retries=config.llm_max_retries,
        )
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
