"""KisanPath-owned voice errors exposed by every STT/TTS adapter."""

from __future__ import annotations


class VoiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code


class VoiceConfigurationError(VoiceError):
    pass


class VoiceAuthenticationError(VoiceError):
    pass


class VoiceRateLimitError(VoiceError):
    pass


class VoiceTimeoutError(VoiceError):
    pass


class VoiceUnavailableError(VoiceError):
    pass


class VoiceInvalidRequestError(VoiceError):
    pass


class VoiceResponseError(VoiceError):
    pass
