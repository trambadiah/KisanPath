"""Non-secret voice configuration with runtime-only credential lookup."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kisanpath.voice.exceptions import VoiceConfigurationError
from kisanpath.voice.tts.models import SpeechAudioFormat


class VoiceProviderSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    base_url: str | None = None
    timeout_seconds: float = Field(default=30, gt=0, le=600)

    @field_validator("base_url")
    @classmethod
    def valid_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        return value.rstrip("/")

    def resolve_api_key(
        self,
        environ: Mapping[str, str],
        *,
        alias: str,
        required: bool = True,
    ) -> str | None:
        value = environ.get(self.api_key_env, "") if self.api_key_env else ""
        if required and not value:
            variable = self.api_key_env or "an API-key environment variable"
            raise VoiceConfigurationError(
                f"Voice provider '{alias}' requires a value in {variable}",
                provider=alias,
                model=self.model,
            )
        return value or None


class STTProviderSettings(VoiceProviderSettings):
    include_logprobs: bool = True


class TTSProviderSettings(VoiceProviderSettings):
    voice: str = Field(default="alloy", min_length=1)
    audio_format: SpeechAudioFormat = SpeechAudioFormat.MP3
    speed: float = Field(default=1, ge=0.25, le=4)


def _default_stt() -> dict[str, STTProviderSettings]:
    return {
        "openai": STTProviderSettings(
            adapter="openai",
            model="gpt-4o-mini-transcribe",
            api_key_env="OPENAI_API_KEY",
        )
    }


def _default_tts() -> dict[str, TTSProviderSettings]:
    return {
        "openai": TTSProviderSettings(
            adapter="openai",
            model="tts-1",
            api_key_env="OPENAI_API_KEY",
            voice="alloy",
        )
    }


class VoiceSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    stt_provider: str = "openai"
    tts_provider: str = "openai"
    stt_providers: dict[str, STTProviderSettings] = Field(default_factory=_default_stt)
    tts_providers: dict[str, TTSProviderSettings] = Field(default_factory=_default_tts)

    @model_validator(mode="after")
    def selected_providers_exist(self) -> VoiceSettings:
        if self.stt_provider not in self.stt_providers:
            raise ValueError("selected STT provider is not configured")
        if self.tts_provider not in self.tts_providers:
            raise ValueError("selected TTS provider is not configured")
        return self


def load_voice_settings(
    path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> VoiceSettings:
    env = os.environ if environ is None else environ
    config_path = path or env.get("KISANPATH_VOICE_CONFIG")
    raw: dict[str, Any] = {}
    if config_path:
        resolved = Path(config_path)
        try:
            with resolved.open("rb") as handle:
                document = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise VoiceConfigurationError(
                f"Unable to load voice config from {resolved}"
            ) from exc
        voice = document.get("voice", document)
        if not isinstance(voice, dict):
            raise VoiceConfigurationError("voice configuration must be a table")
        raw = dict(voice)

    if value := env.get("STT_PROVIDER"):
        raw["stt_provider"] = value
    if value := env.get("TTS_PROVIDER"):
        raw["tts_provider"] = value

    stt_providers = dict(raw.get("stt_providers", {})) if config_path else {
        alias: item.model_dump() for alias, item in _default_stt().items()
    }
    tts_providers = dict(raw.get("tts_providers", {})) if config_path else {
        alias: item.model_dump() for alias, item in _default_tts().items()
    }
    selected_stt = raw.get("stt_provider", "openai")
    selected_tts = raw.get("tts_provider", "openai")
    if model := env.get("STT_MODEL"):
        data = dict(stt_providers.get(selected_stt, {}))
        data["model"] = model
        stt_providers[selected_stt] = data
    if model := env.get("TTS_MODEL"):
        data = dict(tts_providers.get(selected_tts, {}))
        data["model"] = model
        tts_providers[selected_tts] = data
    if voice := env.get("TTS_VOICE"):
        data = dict(tts_providers.get(selected_tts, {}))
        data["voice"] = voice
        tts_providers[selected_tts] = data
    raw["stt_providers"] = stt_providers
    raw["tts_providers"] = tts_providers
    try:
        return VoiceSettings.model_validate(raw)
    except ValueError as exc:
        raise VoiceConfigurationError("Invalid voice configuration") from exc
