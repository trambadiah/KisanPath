from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from kisanpath.domain.profile import LanguageCode
from kisanpath.voice.exceptions import VoiceRateLimitError, VoiceResponseError
from kisanpath.voice.stt.models import AudioInput, AudioMediaType, TranscriptionRequest
from kisanpath.voice.stt.providers.openai import OpenAISTTClient
from kisanpath.voice.tts.models import SpeechAudioFormat, SynthesisRequest
from kisanpath.voice.tts.providers.openai import OpenAITTSClient


class AsyncCall:
    def __init__(self, result: object) -> None:
        self.result = result
        self.kwargs: dict[str, object] = {}

    async def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class Models:
    async def retrieve(self, model: str) -> object:
        return {"id": model}


class ProviderRateLimitError(Exception):
    status_code = 429


@pytest.mark.asyncio
async def test_openai_stt_normalizes_transcript_confidence_and_request() -> None:
    transcription = AsyncCall(
        {
            "text": "મારી પાસે 3 એકર જમીન છે",
            "language": "gu",
            "logprobs": [{"logprob": math.log(0.9)}, {"logprob": math.log(0.81)}],
        }
    )
    client = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=transcription), models=Models()
    )
    adapter = OpenAISTTClient(
        alias="openai-stt", model="gpt-4o-mini-transcribe", client=client
    )

    result = await adapter.transcribe(
        TranscriptionRequest(
            request_id="voice-1",
            audio=AudioInput(
                content=b"synthetic-audio",
                filename="farmer.wav",
                media_type=AudioMediaType.WAV,
            ),
            language_hint=LanguageCode.GUJARATI,
        )
    )

    assert result.provider == "openai-stt"
    assert result.language is LanguageCode.GUJARATI
    assert result.confidence == pytest.approx(math.sqrt(0.9 * 0.81))
    assert result.segments[0].confidence == result.confidence
    assert transcription.kwargs["language"] == "gu"
    assert transcription.kwargs["include"] == ["logprobs"]
    assert transcription.kwargs["file"] == (
        "farmer.wav",
        b"synthetic-audio",
        "audio/wav",
    )
    assert (await adapter.healthcheck()).available is True


@pytest.mark.asyncio
async def test_openai_stt_normalizes_provider_error() -> None:
    client = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=AsyncCall(ProviderRateLimitError())),
        models=Models(),
    )
    adapter = OpenAISTTClient(alias="openai", model="transcribe", client=client)
    with pytest.raises(VoiceRateLimitError):
        await adapter.transcribe(
            TranscriptionRequest(
                request_id="voice-rate",
                audio=AudioInput(
                    content=b"audio",
                    filename="audio.wav",
                    media_type=AudioMediaType.WAV,
                ),
            )
        )


@pytest.mark.asyncio
async def test_openai_stt_rejects_malformed_provider_response_locally() -> None:
    client = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=AsyncCall({"text": ""})),
        models=Models(),
    )
    adapter = OpenAISTTClient(alias="openai", model="transcribe", client=client)
    with pytest.raises(VoiceResponseError):
        await adapter.transcribe(
            TranscriptionRequest(
                request_id="voice-malformed",
                audio=AudioInput(
                    content=b"audio",
                    filename="audio.wav",
                    media_type=AudioMediaType.WAV,
                ),
            )
        )


@pytest.mark.asyncio
async def test_openai_tts_normalizes_binary_audio_and_request() -> None:
    speech = AsyncCall(SimpleNamespace(content=b"synthetic-mp3"))
    client = SimpleNamespace(audio=SimpleNamespace(speech=speech), models=Models())
    adapter = OpenAITTSClient(
        alias="openai-tts", model="tts-1", voice="alloy", client=client
    )

    result = await adapter.synthesize(
        SynthesisRequest(
            request_id="speech-1",
            text="તમારી જમીન કેટલી છે?",
            language=LanguageCode.GUJARATI,
            audio_format=SpeechAudioFormat.MP3,
        )
    )

    assert result.audio == b"synthetic-mp3"
    assert result.media_type == "audio/mpeg"
    assert result.voice == "alloy"
    assert speech.kwargs["response_format"] == "mp3"
    assert speech.kwargs["input"] == "તમારી જમીન કેટલી છે?"
    assert (await adapter.healthcheck()).available is True


@pytest.mark.asyncio
async def test_openai_tts_rejects_empty_provider_audio_locally() -> None:
    speech = AsyncCall(SimpleNamespace(content=b""))
    client = SimpleNamespace(audio=SimpleNamespace(speech=speech), models=Models())
    adapter = OpenAITTSClient(alias="openai", model="tts-1", voice="alloy", client=client)

    with pytest.raises(VoiceResponseError):
        await adapter.synthesize(
            SynthesisRequest(
                request_id="speech-empty",
                text="Please confirm your land area.",
                language=LanguageCode.ENGLISH,
            )
        )
