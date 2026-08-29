"""Extensible STT/TTS adapter registries."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from kisanpath.voice.config import STTProviderSettings, TTSProviderSettings
from kisanpath.voice.exceptions import VoiceConfigurationError
from kisanpath.voice.stt.base import STTClient
from kisanpath.voice.tts.base import TTSClient

STTFactory = Callable[[str, STTProviderSettings, Mapping[str, str]], STTClient]
TTSFactory = Callable[[str, TTSProviderSettings, Mapping[str, str]], TTSClient]


class STTRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, STTFactory] = {}

    def register(self, adapter: str, factory: STTFactory) -> None:
        if adapter in self._factories:
            raise VoiceConfigurationError(f"STT adapter '{adapter}' is already registered")
        self._factories[adapter] = factory

    def create(
        self,
        alias: str,
        settings: STTProviderSettings,
        environ: Mapping[str, str],
    ) -> STTClient:
        factory = self._factories.get(settings.adapter)
        if factory is None:
            raise VoiceConfigurationError(
                f"STT adapter '{settings.adapter}' is not registered", provider=alias
            )
        return factory(alias, settings, environ)


class TTSRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, TTSFactory] = {}

    def register(self, adapter: str, factory: TTSFactory) -> None:
        if adapter in self._factories:
            raise VoiceConfigurationError(f"TTS adapter '{adapter}' is already registered")
        self._factories[adapter] = factory

    def create(
        self,
        alias: str,
        settings: TTSProviderSettings,
        environ: Mapping[str, str],
    ) -> TTSClient:
        factory = self._factories.get(settings.adapter)
        if factory is None:
            raise VoiceConfigurationError(
                f"TTS adapter '{settings.adapter}' is not registered", provider=alias
            )
        return factory(alias, settings, environ)


def create_builtin_stt_registry() -> STTRegistry:
    from kisanpath.voice.stt.providers.openai import create_openai_stt_client

    registry = STTRegistry()
    registry.register("openai", create_openai_stt_client)
    return registry


def create_builtin_tts_registry() -> TTSRegistry:
    from kisanpath.voice.tts.providers.openai import create_openai_tts_client

    registry = TTSRegistry()
    registry.register("openai", create_openai_tts_client)
    return registry
