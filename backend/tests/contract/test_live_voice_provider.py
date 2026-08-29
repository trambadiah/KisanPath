from __future__ import annotations

import os

import pytest

from kisanpath.domain.profile import LanguageCode
from kisanpath.voice import (
    create_builtin_stt_registry,
    create_builtin_tts_registry,
    load_voice_settings,
)
from kisanpath.voice.stt import AudioInput, AudioMediaType, TranscriptionRequest
from kisanpath.voice.tts import SpeechAudioFormat, SynthesisRequest

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_live_openai_voice_round_trip_is_opt_in() -> None:
    if os.environ.get("KISANPATH_RUN_LIVE_VOICE_TESTS") != "1":
        pytest.skip("set KISANPATH_RUN_LIVE_VOICE_TESTS=1 to run live voice tests")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is not configured")

    settings = load_voice_settings(environ=os.environ)
    tts = create_builtin_tts_registry().create(
        settings.tts_provider,
        settings.tts_providers[settings.tts_provider],
        os.environ,
    )
    stt = create_builtin_stt_registry().create(
        settings.stt_provider,
        settings.stt_providers[settings.stt_provider],
        os.environ,
    )
    speech = await tts.synthesize(
        SynthesisRequest(
            request_id="live-synthetic-speech",
            text="This is synthetic test audio about three acres of land.",
            language=LanguageCode.ENGLISH,
            audio_format=SpeechAudioFormat.MP3,
        )
    )
    transcript = await stt.transcribe(
        TranscriptionRequest(
            request_id="live-synthetic-transcript",
            audio=AudioInput(
                content=speech.audio,
                filename="synthetic-farmer.mp3",
                media_type=AudioMediaType.MPEG,
            ),
            language_hint=LanguageCode.ENGLISH,
        )
    )

    assert transcript.text
    assert transcript.provider == settings.stt_provider
