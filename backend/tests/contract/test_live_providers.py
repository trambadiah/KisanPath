"""Minimal live smoke tests. Never run unless explicitly opted in."""

from __future__ import annotations

import os

import pytest

from kisanpath.llm.config import ProviderSettings
from kisanpath.llm.models import LLMMessage, LLMRequest, MessageRole
from kisanpath.llm.registry import create_builtin_registry

LIVE_FLAG = "KISANPATH_RUN_LIVE_LLM_TESTS"


def _live_settings(provider: str) -> ProviderSettings:
    definitions = {
        "openai": (
            "openai",
            "KISANPATH_OPENAI_TEST_MODEL",
            "OPENAI_API_KEY",
            None,
        ),
        "anthropic": (
            "anthropic",
            "KISANPATH_ANTHROPIC_TEST_MODEL",
            "ANTHROPIC_API_KEY",
            None,
        ),
        "gemini": (
            "gemini",
            "KISANPATH_GEMINI_TEST_MODEL",
            "GEMINI_API_KEY",
            None,
        ),
        "ollama": (
            "ollama",
            "KISANPATH_OLLAMA_TEST_MODEL",
            None,
            os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        ),
        "openai_compatible": (
            "openai_compatible",
            "KISANPATH_OPENAI_COMPATIBLE_TEST_MODEL",
            "OPENAI_COMPATIBLE_API_KEY",
            os.environ.get("OPENAI_COMPATIBLE_BASE_URL"),
        ),
    }
    adapter, model_env, key_env, base_url = definitions[provider]
    model = os.environ.get(model_env)
    if not model:
        pytest.skip(f"{model_env} is not configured")
    if key_env and provider != "openai_compatible" and not os.environ.get(key_env):
        pytest.skip(f"{key_env} is not configured")
    if provider == "openai_compatible" and not base_url:
        pytest.skip("OPENAI_COMPATIBLE_BASE_URL is not configured")
    return ProviderSettings(
        adapter=adapter,
        model=model,
        api_key_env=key_env,
        base_url=base_url,
        timeout_seconds=30,
    )


@pytest.mark.live
@pytest.mark.parametrize(
    "provider", ["openai", "anthropic", "gemini", "ollama", "openai_compatible"]
)
async def test_live_plain_generation(provider: str) -> None:
    if os.environ.get(LIVE_FLAG) != "1":
        pytest.skip(f"set {LIVE_FLAG}=1 to run live provider tests")
    settings = _live_settings(provider)
    client = create_builtin_registry().create(provider, settings, os.environ)

    response = await client.generate(
        LLMRequest(
            messages=(
                LLMMessage(
                    role=MessageRole.USER,
                    content="Reply with exactly the word KisanPath.",
                ),
            ),
            max_output_tokens=16,
            temperature=0,
        )
    )

    assert response.text.strip()
    assert response.provider == provider
