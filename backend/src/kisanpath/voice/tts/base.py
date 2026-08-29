"""Text-to-speech adapter contract."""

from __future__ import annotations

from typing import Protocol

from kisanpath.voice.tts.models import (
    SynthesisRequest,
    SynthesisResult,
    TTSCapabilities,
    TTSHealth,
)


class TTSClient(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def capabilities(self) -> TTSCapabilities: ...

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult: ...

    async def healthcheck(self) -> TTSHealth: ...
