"""OpenAI speech-to-text adapter; SDK types do not cross this module boundary."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Mapping
from time import monotonic
from typing import Any

from kisanpath.domain.profile import LanguageCode
from kisanpath.voice._errors import normalize_voice_error
from kisanpath.voice.config import STTProviderSettings
from kisanpath.voice.exceptions import VoiceConfigurationError, VoiceResponseError
from kisanpath.voice.stt.models import (
    STTCapabilities,
    STTHealth,
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptSegment,
)


def _value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


class OpenAISTTClient:
    def __init__(
        self,
        *,
        alias: str,
        model: str,
        client: Any,
        timeout_seconds: float = 30,
        include_logprobs: bool = True,
    ) -> None:
        self._alias = alias
        self._model = model
        self._client = client
        self._timeout_seconds = timeout_seconds
        self._include_logprobs = include_logprobs

    @property
    def provider(self) -> str:
        return self._alias

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> STTCapabilities:
        return STTCapabilities(
            confidence=self._include_logprobs,
            segment_timestamps=False,
            alternatives=False,
            language_hints=True,
        )

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        started = monotonic()
        kwargs: dict[str, Any] = {
            "file": (
                request.audio.filename,
                request.audio.content,
                request.audio.media_type.value,
            ),
            "model": self._model,
            "response_format": "json",
        }
        if request.language_hint not in {None, LanguageCode.UNDETERMINED}:
            assert request.language_hint is not None
            kwargs["language"] = request.language_hint.value
        if request.prompt:
            kwargs["prompt"] = request.prompt
        if self._include_logprobs:
            kwargs["include"] = ["logprobs"]
        try:
            async with asyncio.timeout(request.timeout_seconds or self._timeout_seconds):
                raw = await self._client.audio.transcriptions.create(**kwargs)
        except Exception as exc:
            raise normalize_voice_error(exc, provider=self._alias, model=self._model) from exc

        try:
            text = str(_value(raw, "text", "")).strip()
            if not text:
                raise ValueError("empty transcript")
            confidence = self._confidence(_value(raw, "logprobs", None))
            raw_segments = _value(raw, "segments", None) or ()
            segments = tuple(
                TranscriptSegment(
                    segment_id=str(_value(item, "id", index)),
                    text=str(_value(item, "text", "")).strip(),
                    start_seconds=_value(item, "start", None),
                    end_seconds=_value(item, "end", None),
                    confidence=(
                        segment_confidence
                        if (segment_confidence := self._segment_confidence(item)) is not None
                        else confidence
                    ),
                )
                for index, item in enumerate(raw_segments)
                if str(_value(item, "text", "")).strip()
            )
            if not segments:
                segments = (
                    TranscriptSegment(
                        segment_id="segment-0",
                        text=text,
                        confidence=confidence,
                    ),
                )
            return TranscriptionResult(
                transcript_id=request.request_id,
                text=text,
                language=self._language(_value(raw, "language", None), request.language_hint),
                confidence=confidence,
                segments=segments,
                provider=self._alias,
                model=self._model,
                latency_ms=round((monotonic() - started) * 1000),
            )
        except (TypeError, ValueError) as exc:
            raise VoiceResponseError(
                "speech-to-text provider returned an invalid transcript",
                provider=self._alias,
                model=self._model,
            ) from exc

    async def healthcheck(self) -> STTHealth:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                await self._client.models.retrieve(self._model)
            return STTHealth(available=True, provider=self._alias, model=self._model)
        except Exception as exc:
            normalized = normalize_voice_error(exc, provider=self._alias, model=self._model)
            return STTHealth(
                available=False,
                provider=self._alias,
                model=self._model,
                detail=type(normalized).__name__,
            )

    @staticmethod
    def _confidence(logprobs: Any) -> float | None:
        if not logprobs:
            return None
        values = [
            float(value)
            for item in logprobs
            if (value := _value(item, "logprob", None)) is not None
        ]
        if not values:
            return None
        return max(0.0, min(1.0, math.exp(sum(values) / len(values))))

    @staticmethod
    def _segment_confidence(segment: Any) -> float | None:
        average = _value(segment, "avg_logprob", None)
        if average is None:
            return None
        return max(0.0, min(1.0, math.exp(float(average))))

    @staticmethod
    def _language(value: Any, hint: LanguageCode | None) -> LanguageCode:
        normalized = str(value or "").casefold()
        aliases = {
            "gu": LanguageCode.GUJARATI,
            "gujarati": LanguageCode.GUJARATI,
            "hi": LanguageCode.HINDI,
            "hindi": LanguageCode.HINDI,
            "en": LanguageCode.ENGLISH,
            "english": LanguageCode.ENGLISH,
        }
        return aliases.get(normalized, hint or LanguageCode.UNDETERMINED)


def create_openai_stt_client(
    alias: str,
    settings: STTProviderSettings,
    environ: Mapping[str, str],
) -> OpenAISTTClient:
    api_key = settings.resolve_api_key(environ, alias=alias)
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise VoiceConfigurationError(
            "OpenAI STT adapter requires the 'openai' package",
            provider=alias,
            model=settings.model,
        ) from exc
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
    )
    return OpenAISTTClient(
        alias=alias,
        model=settings.model,
        client=client,
        timeout_seconds=settings.timeout_seconds,
        include_logprobs=settings.include_logprobs,
    )
