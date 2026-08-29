"""Provider-independent text-to-speech boundary."""

from kisanpath.voice.tts.base import TTSClient
from kisanpath.voice.tts.models import (
    SpeechAudioFormat,
    SynthesisRequest,
    SynthesisResult,
    TTSCapabilities,
    TTSHealth,
)

__all__ = [
    "SpeechAudioFormat",
    "SynthesisRequest",
    "SynthesisResult",
    "TTSCapabilities",
    "TTSClient",
    "TTSHealth",
]
