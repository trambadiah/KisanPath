"""Provider-independent speech-to-text request and response models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kisanpath.domain.profile import LanguageCode


class AudioMediaType(StrEnum):
    WAV = "audio/wav"
    MPEG = "audio/mpeg"
    MP4 = "audio/mp4"
    M4A = "audio/x-m4a"
    WEBM = "audio/webm"
    OGG = "audio/ogg"
    FLAC = "audio/flac"


class AudioInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    content: bytes = Field(min_length=1, max_length=25 * 1024 * 1024)
    filename: str = Field(min_length=1, max_length=255, pattern=r"^[^/\\]+$")
    media_type: AudioMediaType


class TranscriptionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1)
    audio: AudioInput
    language_hint: LanguageCode | None = None
    prompt: str | None = Field(default=None, min_length=1, max_length=1000)
    timeout_seconds: float | None = Field(default=None, gt=0, le=600)


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    segment_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=5000)
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def valid_window(self) -> TranscriptSegment:
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds < self.start_seconds
        ):
            raise ValueError("segment end cannot precede its start")
        return self


class TranscriptAlternative(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1, max_length=500)
    confidence: float | None = Field(default=None, ge=0, le=1)


class TranscriptAmbiguity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ambiguity_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=500)
    segment_ids: tuple[str, ...] = ()
    alternatives: tuple[TranscriptAlternative, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def unique_alternatives(self) -> TranscriptAmbiguity:
        values = tuple(item.text.casefold() for item in self.alternatives)
        if len(values) != len(set(values)):
            raise ValueError("transcript alternatives must be unique")
        return self


class TranscriptionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    transcript_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=50000)
    language: LanguageCode = LanguageCode.UNDETERMINED
    confidence: float | None = Field(default=None, ge=0, le=1)
    segments: tuple[TranscriptSegment, ...] = ()
    ambiguities: tuple[TranscriptAmbiguity, ...] = ()
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    latency_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def valid_references(self) -> TranscriptionResult:
        segment_ids = tuple(item.segment_id for item in self.segments)
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("transcript segment IDs must be unique")
        ambiguity_ids = tuple(item.ambiguity_id for item in self.ambiguities)
        if len(ambiguity_ids) != len(set(ambiguity_ids)):
            raise ValueError("transcript ambiguity IDs must be unique")
        missing = {
            segment_id
            for ambiguity in self.ambiguities
            for segment_id in ambiguity.segment_ids
            if segment_id not in segment_ids
        }
        if missing:
            raise ValueError("transcript ambiguities reference unknown segments")
        return self


class STTCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    confidence: bool
    segment_timestamps: bool
    alternatives: bool
    language_hints: bool


class STTHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    available: bool
    provider: str
    model: str
    detail: str | None = None
