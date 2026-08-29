"""Transcribe synthetic/local audio and synthesize a short response via voice ports."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from kisanpath.domain.profile import LanguageCode
from kisanpath.voice import (
    create_builtin_stt_registry,
    create_builtin_tts_registry,
    load_voice_settings,
)
from kisanpath.voice.stt import AudioInput, AudioMediaType, TranscriptionRequest
from kisanpath.voice.tts import SynthesisRequest


async def main(audio_path: Path) -> None:
    audio_content = await asyncio.to_thread(audio_path.read_bytes)
    settings = load_voice_settings("examples/voice.example.toml")
    stt_settings = settings.stt_providers[settings.stt_provider]
    tts_settings = settings.tts_providers[settings.tts_provider]
    stt = create_builtin_stt_registry().create(
        settings.stt_provider, stt_settings, os.environ
    )
    tts = create_builtin_tts_registry().create(
        settings.tts_provider, tts_settings, os.environ
    )
    transcript = await stt.transcribe(
        TranscriptionRequest(
            request_id="example-transcript",
            audio=AudioInput(
                content=audio_content,
                filename=audio_path.name,
                media_type=AudioMediaType.WAV,
            ),
            language_hint=LanguageCode.GUJARATI,
        )
    )
    print(transcript.model_dump_json(indent=2))
    speech = await tts.synthesize(
        SynthesisRequest(
            request_id="example-speech",
            text="તમારી માહિતી મળી ગઈ છે.",
            language=LanguageCode.GUJARATI,
        )
    )
    await asyncio.to_thread(Path("response.mp3").write_bytes, speech.audio)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path, help="WAV audio file to transcribe")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.audio))
