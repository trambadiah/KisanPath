"""Provider-independent text-to-speech request and response models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from kisanpath.domain.profile import LanguageCode


class SpeechAudioFormat(StrEnum):
    MP3 = "mp3"
    OPUS = "opus"
    AAC = "aac"
    FLAC = "flac"
    WAV = "wav"
    PCM = "pcm"

    @property
    def media_type(self) -> str:
        return {
            self.MP3: "audio/mpeg",
            self.OPUS: "audio/ogg; codecs=opus",
            self.AAC: "audio/aac",
            self.FLAC: "audio/flac",
            self.WAV: "audio/wav",
            self.PCM: "audio/L16",
        }[self]


class SynthesisRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=4096)
    language: LanguageCode
    voice: str | None = Field(default=None, min_length=1)
    audio_format: SpeechAudioFormat | None = None
    speed: float | None = Field(default=None, ge=0.25, le=4)
    instructions: str | None = Field(default=None, min_length=1, max_length=1000)
    timeout_seconds: float | None = Field(default=None, gt=0, le=600)


class SynthesisResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1)
    audio: bytes = Field(min_length=1)
    media_type: str = Field(min_length=1)
    audio_format: SpeechAudioFormat
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    voice: str = Field(min_length=1)
    latency_ms: int | None = Field(default=None, ge=0)


class TTSCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    audio_formats: frozenset[SpeechAudioFormat]
    configurable_voice: bool
    configurable_speed: bool
    instructions: bool


class TTSHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    available: bool
    provider: str
    model: str
    detail: str | None = None
