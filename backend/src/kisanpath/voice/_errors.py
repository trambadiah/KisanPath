"""Provider-error normalization shared by STT and TTS adapters."""

from __future__ import annotations

import asyncio

from kisanpath.voice.exceptions import (
    VoiceAuthenticationError,
    VoiceError,
    VoiceInvalidRequestError,
    VoiceRateLimitError,
    VoiceTimeoutError,
    VoiceUnavailableError,
)


def normalize_voice_error(
    exc: Exception,
    *,
    provider: str,
    model: str,
) -> VoiceError:
    if isinstance(exc, VoiceError):
        return exc
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.casefold()
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timeout" in name:
        return VoiceTimeoutError(
            "voice provider request timed out",
            provider=provider,
            model=model,
            status_code=status,
        )
    if status in {401, 403} or "authentication" in name or "permission" in name:
        return VoiceAuthenticationError(
            "voice provider authentication failed",
            provider=provider,
            model=model,
            status_code=status,
        )
    if status == 429 or "ratelimit" in name or "rate_limit" in name:
        return VoiceRateLimitError(
            "voice provider rate limit exceeded",
            provider=provider,
            model=model,
            status_code=status,
        )
    if status is not None and 400 <= status < 500:
        return VoiceInvalidRequestError(
            "voice provider rejected the request",
            provider=provider,
            model=model,
            status_code=status,
        )
    return VoiceUnavailableError(
        "voice provider is unavailable",
        provider=provider,
        model=model,
        status_code=status,
    )
