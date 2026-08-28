"""Typed configuration with environment-only secret resolution."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kisanpath.llm.exceptions import LLMConfigurationError
from kisanpath.llm.models import Capability, ProviderCapabilities


class ProviderSettings(BaseModel):
    """Non-secret provider configuration.

    `api_key_env` stores only the environment-variable name. Configuration files
    containing an `api_key` field are rejected by the `extra="forbid"` policy.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter: str
    model: str = Field(min_length=1)
    api_key_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    base_url: str | None = None
    timeout_seconds: float = Field(default=30.0, gt=0, le=600)
    capabilities: ProviderCapabilities | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        return value.rstrip("/")

    def resolve_api_key(
        self,
        environ: Mapping[str, str],
        *,
        required: bool,
        alias: str,
    ) -> str | None:
        value = environ.get(self.api_key_env, "") if self.api_key_env else ""
        if required and not value:
            variable = self.api_key_env or "an API-key environment variable"
            raise LLMConfigurationError(
                f"Provider '{alias}' requires a value in {variable}", provider=alias
            )
        return value or None


class RouteSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(min_length=1)
    model: str | None = Field(default=None, min_length=1)
    fallbacks: tuple[str, ...] = ()
    required_capabilities: frozenset[Capability] = frozenset()

    @field_validator("fallbacks")
    @classmethod
    def unique_fallbacks(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("fallback provider aliases must be unique")
        return value


def _default_providers() -> dict[str, ProviderSettings]:
    return {
        "openai": ProviderSettings(
            adapter="openai", model="gpt-5-mini", api_key_env="OPENAI_API_KEY"
        ),
        "anthropic": ProviderSettings(
            adapter="anthropic",
            model="claude-sonnet-4-6",
            api_key_env="ANTHROPIC_API_KEY",
        ),
        "gemini": ProviderSettings(
            adapter="gemini", model="gemini-2.5-flash", api_key_env="GEMINI_API_KEY"
        ),
        "ollama": ProviderSettings(
            adapter="ollama", model="qwen3:8b", base_url="http://localhost:11434"
        ),
        "openai_compatible": ProviderSettings(
            adapter="openai_compatible",
            model="configured-model",
            api_key_env="OPENAI_COMPATIBLE_API_KEY",
            base_url="http://localhost:8000/v1",
        ),
    }


class LLMSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    default: RouteSettings = Field(default_factory=lambda: RouteSettings(provider="openai"))
    agents: dict[str, RouteSettings] = Field(default_factory=dict)
    providers: dict[str, ProviderSettings] = Field(default_factory=_default_providers)
    fallback_enabled: bool = True
    evaluation_fallback_enabled: bool = False

    @model_validator(mode="after")
    def validate_routes(self) -> LLMSettings:
        routes = {"default": self.default, **self.agents}
        for name, route in routes.items():
            aliases = (route.provider, *route.fallbacks)
            missing = [alias for alias in aliases if alias not in self.providers]
            if missing:
                raise ValueError(f"route '{name}' references unknown providers: {missing}")
            if route.provider in route.fallbacks:
                raise ValueError(f"route '{name}' repeats its primary provider as a fallback")
        return self

    def route_for(self, agent: str | None) -> RouteSettings:
        return self.agents.get(agent, self.default) if agent else self.default


def _parse_bool(value: str, *, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise LLMConfigurationError(f"{name} must be a boolean value")


def load_llm_settings(
    path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> LLMSettings:
    """Load `[llm]` from TOML, then apply non-secret environment overrides."""

    env = os.environ if environ is None else environ
    config_path = path or env.get("KISANPATH_LLM_CONFIG")
    raw: dict[str, Any] = {}
    if config_path:
        resolved = Path(config_path)
        try:
            with resolved.open("rb") as handle:
                document = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise LLMConfigurationError(f"Unable to load LLM config from {resolved}") from exc
        llm_section = document.get("llm", document)
        if not isinstance(llm_section, dict):
            raise LLMConfigurationError("LLM configuration must be a table")
        raw = dict(llm_section)

    default = dict(raw.get("default", {}))
    if provider := env.get("LLM_DEFAULT_PROVIDER"):
        default["provider"] = provider
    if model := env.get("LLM_DEFAULT_MODEL"):
        default["model"] = model
    if default:
        raw["default"] = default
    if value := env.get("LLM_FALLBACK_ENABLED"):
        raw["fallback_enabled"] = _parse_bool(value, name="LLM_FALLBACK_ENABLED")
    if value := env.get("LLM_EVALUATION_FALLBACK_ENABLED"):
        raw["evaluation_fallback_enabled"] = _parse_bool(
            value, name="LLM_EVALUATION_FALLBACK_ENABLED"
        )

    defaults = _default_providers()
    providers: dict[str, Any]
    if config_path:
        providers = dict(raw.get("providers", {}))
    else:
        providers = {alias: settings.model_dump() for alias, settings in defaults.items()}
    provider_url_overrides = {
        "ollama": env.get("OLLAMA_BASE_URL"),
        "openai_compatible": env.get("OPENAI_COMPATIBLE_BASE_URL"),
    }
    for alias, base_url in provider_url_overrides.items():
        if not base_url:
            continue
        provider_data = dict(providers.get(alias, defaults[alias].model_dump()))
        provider_data["base_url"] = base_url
        providers[alias] = provider_data
    if providers:
        raw["providers"] = providers
    try:
        return LLMSettings.model_validate(raw)
    except ValueError as exc:
        raise LLMConfigurationError("Invalid LLM configuration") from exc
