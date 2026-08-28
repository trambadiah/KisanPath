"""Provider factory registry; the only switchboard aware of adapter classes."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from kisanpath.llm.base import LLMClient
from kisanpath.llm.config import ProviderSettings
from kisanpath.llm.exceptions import LLMConfigurationError

ProviderFactory = Callable[[str, ProviderSettings, Mapping[str, str]], LLMClient]


class ProviderRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, adapter: str, factory: ProviderFactory) -> None:
        if adapter in self._factories:
            raise LLMConfigurationError(f"Provider adapter '{adapter}' is already registered")
        self._factories[adapter] = factory

    def create(
        self,
        alias: str,
        settings: ProviderSettings,
        environ: Mapping[str, str],
    ) -> LLMClient:
        factory = self._factories.get(settings.adapter)
        if factory is None:
            raise LLMConfigurationError(
                f"Provider adapter '{settings.adapter}' is not registered", provider=alias
            )
        return factory(alias, settings, environ)

    @property
    def adapters(self) -> frozenset[str]:
        return frozenset(self._factories)


def create_builtin_registry() -> ProviderRegistry:
    # Imports stay here rather than in domain/agent code. SDK imports inside these
    # provider modules are lazy, so the core package does not require every extra.
    from kisanpath.llm.providers.anthropic import create_anthropic_client
    from kisanpath.llm.providers.gemini import create_gemini_client
    from kisanpath.llm.providers.ollama import create_ollama_client
    from kisanpath.llm.providers.openai import create_openai_client
    from kisanpath.llm.providers.openai_compatible import create_openai_compatible_client

    registry = ProviderRegistry()
    registry.register("openai", create_openai_client)
    registry.register("anthropic", create_anthropic_client)
    registry.register("gemini", create_gemini_client)
    registry.register("ollama", create_ollama_client)
    registry.register("openai_compatible", create_openai_compatible_client)
    return registry
