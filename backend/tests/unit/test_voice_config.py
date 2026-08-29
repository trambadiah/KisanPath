from __future__ import annotations

import pytest

from kisanpath.voice.config import STTProviderSettings, load_voice_settings
from kisanpath.voice.exceptions import VoiceConfigurationError
from kisanpath.voice.registry import STTRegistry


def test_voice_defaults_and_environment_overrides_are_non_secret() -> None:
    settings = load_voice_settings(
        environ={
            "STT_MODEL": "custom-transcribe",
            "TTS_MODEL": "custom-speech",
            "TTS_VOICE": "sage",
        }
    )

    assert settings.stt_providers["openai"].model == "custom-transcribe"
    assert settings.tts_providers["openai"].model == "custom-speech"
    assert settings.tts_providers["openai"].voice == "sage"
    assert '"api_key":' not in settings.model_dump_json()


def test_voice_configuration_rejects_embedded_secret() -> None:
    with pytest.raises(ValueError):
        STTProviderSettings.model_validate(
            {"adapter": "openai", "model": "transcribe", "api_key": "do-not-store"}
        )


def test_registry_is_extensible_and_missing_adapter_is_normalized() -> None:
    registry = STTRegistry()
    with pytest.raises(VoiceConfigurationError):
        registry.create(
            "future",
            STTProviderSettings(adapter="future", model="local-asr"),
            {},
        )
