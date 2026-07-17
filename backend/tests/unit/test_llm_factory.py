"""Tests for the configured model-provider factory."""

from __future__ import annotations

import pytest

from app.config.settings import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.factory import build_model_provider
from app.llm.mock_provider import MockProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider


def _settings(**overrides: object) -> Settings:
    config = Settings.model_construct(
        llm_provider="mock",
        llm_model="qwen-test",
        llm_api_key="",
        llm_base_url="",
        llm_timeout_seconds=60,
        llm_max_retries=1,
    )
    for field, value in overrides.items():
        setattr(config, field, value)
    return config


def test_factory_builds_mock_provider() -> None:
    assert isinstance(build_model_provider(_settings()), MockProvider)


def test_factory_builds_anthropic_provider() -> None:
    provider = build_model_provider(
        _settings(
            llm_provider="anthropic",
            llm_api_key="test-key",
            llm_base_url="https://anthropic.example",
        )
    )
    assert isinstance(provider, AnthropicProvider)
    assert provider.provider_name == "anthropic"


def test_factory_builds_openai_compatible_provider() -> None:
    provider = build_model_provider(
        _settings(
            llm_provider="openai_compatible",
            llm_api_key="test-key",
            llm_base_url="https://workspace.example/compatible-mode/v1",
        )
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.provider_name == "openai_compatible"


@pytest.mark.parametrize("missing_field", ["llm_api_key", "llm_base_url"])
def test_openai_compatible_config_must_be_complete(missing_field: str) -> None:
    values = {
        "llm_provider": "openai_compatible",
        "llm_api_key": "test-key",
        "llm_base_url": "https://workspace.example/compatible-mode/v1",
    }
    values[missing_field] = ""

    with pytest.raises(RuntimeError, match="configuration is incomplete"):
        build_model_provider(_settings(**values))


def test_unknown_provider_fails_explicitly() -> None:
    with pytest.raises(RuntimeError, match="Unsupported LLM_PROVIDER"):
        build_model_provider(_settings(llm_provider="unknown"))
