from __future__ import annotations

from pathlib import Path

import pytest

from kisanpath.llm.config import LLMSettings, ProviderSettings, load_llm_settings
from kisanpath.llm.exceptions import LLMConfigurationError


def test_toml_config_supports_per_agent_routes(tmp_path: Path) -> None:
    config = tmp_path / "llm.toml"
    config.write_text(
        """
[llm]
fallback_enabled = true
evaluation_fallback_enabled = false

[llm.default]
provider = "local"

[llm.agents.profile]
provider = "cloud"
model = "profile-model"
fallbacks = ["local"]

[llm.providers.local]
adapter = "ollama"
model = "local-model"
base_url = "http://localhost:11434"

[llm.providers.cloud]
adapter = "openai"
model = "cloud-model"
api_key_env = "TEST_OPENAI_KEY"
""".strip(),
        encoding="utf-8",
    )

    settings = load_llm_settings(config, environ={})

    assert settings.route_for("profile").provider == "cloud"
    assert settings.route_for("unknown").provider == "local"
    assert settings.evaluation_fallback_enabled is False


def test_environment_overrides_non_secret_route_values() -> None:
    settings = load_llm_settings(
        environ={
            "LLM_DEFAULT_PROVIDER": "ollama",
            "LLM_DEFAULT_MODEL": "test-local",
            "LLM_FALLBACK_ENABLED": "false",
        }
    )
    assert settings.default.provider == "ollama"
    assert settings.default.model == "test-local"
    assert settings.fallback_enabled is False


def test_environment_overrides_local_provider_urls() -> None:
    settings = load_llm_settings(
        environ={
            "OLLAMA_BASE_URL": "http://ollama.internal:11434/",
            "OPENAI_COMPATIBLE_BASE_URL": "https://models.internal/v1/",
        }
    )
    assert settings.providers["ollama"].base_url == "http://ollama.internal:11434"
    assert settings.providers["openai_compatible"].base_url == "https://models.internal/v1"


def test_provider_rejects_relative_base_url() -> None:
    with pytest.raises(ValueError):
        ProviderSettings(adapter="ollama", model="test", base_url="localhost:11434")


def test_secret_value_is_rejected_from_configuration(tmp_path: Path) -> None:
    config = tmp_path / "secret.toml"
    config.write_text(
        """
[llm.default]
provider = "unsafe"

[llm.providers.unsafe]
adapter = "openai"
model = "test"
api_key = ""
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(LLMConfigurationError):
        load_llm_settings(config, environ={})

    with pytest.raises(ValueError):
        ProviderSettings.model_validate(
            {"adapter": "openai", "model": "test", "api_key": "must-not-be-here"}
        )


def test_provider_resolves_only_named_environment_secret() -> None:
    settings = ProviderSettings(adapter="openai", model="test", api_key_env="KISANPATH_TEST_KEY")
    assert (
        settings.resolve_api_key(
            {"KISANPATH_TEST_KEY": "runtime-secret"}, required=True, alias="test"
        )
        == "runtime-secret"
    )
    with pytest.raises(LLMConfigurationError):
        settings.resolve_api_key({}, required=True, alias="test")


def test_unknown_provider_route_is_rejected() -> None:
    with pytest.raises(ValueError):
        LLMSettings.model_validate({"default": {"provider": "missing"}})
