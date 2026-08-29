"""Speech-to-text adapter contract."""

from __future__ import annotations

from typing import Protocol

from kisanpath.voice.stt.models import (
    STTCapabilities,
    STTHealth,
    TranscriptionRequest,
    TranscriptionResult,
)


class STTClient(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def capabilities(self) -> STTCapabilities: ...

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult: ...

    async def healthcheck(self) -> STTHealth: ...
