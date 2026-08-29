"""Provider-independent speech-to-text boundary."""

from kisanpath.voice.stt.base import STTClient
from kisanpath.voice.stt.models import (
    AudioInput,
    AudioMediaType,
    STTCapabilities,
    STTHealth,
    TranscriptAlternative,
    TranscriptAmbiguity,
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptSegment,
)

__all__ = [
    "AudioInput",
    "AudioMediaType",
    "STTCapabilities",
    "STTClient",
    "STTHealth",
    "TranscriptAlternative",
    "TranscriptAmbiguity",
    "TranscriptSegment",
    "TranscriptionRequest",
    "TranscriptionResult",
]
