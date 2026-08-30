"""OpenAI text-to-speech adapter; SDK types do not cross this module boundary."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from time import monotonic
from typing import Any

from kisanpath.voice._errors import normalize_voice_error
from kisanpath.voice.config import TTSProviderSettings
from kisanpath.voice.exceptions import VoiceConfigurationError, VoiceResponseError
from kisanpath.voice.tts.models import (
    SpeechAudioFormat,
    SynthesisRequest,
    SynthesisResult,
    TTSCapabilities,
    TTSHealth,
)


class OpenAITTSClient:
    def __init__(
        self,
        *,
        alias: str,
        model: str,
        voice: str,
        client: Any,
        timeout_seconds: float = 30,
        default_format: SpeechAudioFormat = SpeechAudioFormat.MP3,
        default_speed: float = 1,
    ) -> None:
        self._alias = alias
        self._model = model
        self._voice = voice
        self._client = client
        self._timeout_seconds = timeout_seconds
        self._default_format = default_format
        self._default_speed = default_speed

    @property
    def provider(self) -> str:
        return self._alias

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> TTSCapabilities:
        return TTSCapabilities(
            audio_formats=frozenset(SpeechAudioFormat),
            configurable_voice=True,
            configurable_speed=True,
            instructions=self._model.startswith("gpt-4o-mini-tts"),
        )

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        started = monotonic()
        voice = request.voice or self._voice
        audio_format = request.audio_format or self._default_format
        kwargs: dict[str, Any] = {
            "input": request.text,
            "model": self._model,
            "voice": voice,
            "response_format": audio_format.value,
            "speed": request.speed or self._default_speed,
        }
        if request.instructions:
            if not self.capabilities.instructions:
                raise VoiceConfigurationError(
                    f"model '{self._model}' does not support TTS instructions",
                    provider=self._alias,
                    model=self._model,
                )
            kwargs["instructions"] = request.instructions
        try:
            async with asyncio.timeout(request.timeout_seconds or self._timeout_seconds):
                raw = await self._client.audio.speech.create(**kwargs)
                audio = await self._read_audio(raw)
        except Exception as exc:
            raise normalize_voice_error(exc, provider=self._alias, model=self._model) from exc
        if not audio:
            raise VoiceResponseError(
                "text-to-speech provider returned empty audio",
                provider=self._alias,
                model=self._model,
            )
        return SynthesisResult(
            request_id=request.request_id,
            audio=audio,
            media_type=audio_format.media_type,
            audio_format=audio_format,
            provider=self._alias,
            model=self._model,
            voice=voice,
            latency_ms=round((monotonic() - started) * 1000),
        )

    async def healthcheck(self) -> TTSHealth:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                await self._client.models.retrieve(self._model)
            return TTSHealth(available=True, provider=self._alias, model=self._model)
        except Exception as exc:
            normalized = normalize_voice_error(exc, provider=self._alias, model=self._model)
            return TTSHealth(
                available=False,
                provider=self._alias,
                model=self._model,
                detail=type(normalized).__name__,
            )

    @staticmethod
    async def _read_audio(raw: Any) -> bytes:
        if isinstance(raw, bytes):
            return raw
        content = getattr(raw, "content", None)
        if isinstance(content, bytes):
            return content
        reader = getattr(raw, "aread", None)
        if callable(reader):
            result = await reader()
            if isinstance(result, bytes):
                return result
        return b""


def create_openai_tts_client(
    alias: str,
    settings: TTSProviderSettings,
    environ: Mapping[str, str],
) -> OpenAITTSClient:
    api_key = settings.resolve_api_key(environ, alias=alias)
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise VoiceConfigurationError(
            "OpenAI TTS adapter requires the 'openai' package",
            provider=alias,
            model=settings.model,
        ) from exc
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
    )
    return OpenAITTSClient(
        alias=alias,
        model=settings.model,
        voice=settings.voice,
        client=client,
        timeout_seconds=settings.timeout_seconds,
        default_format=settings.audio_format,
        default_speed=settings.speed,
    )
