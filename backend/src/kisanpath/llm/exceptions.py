"""KisanPath-owned exception hierarchy for all LLM providers."""

from __future__ import annotations


class LLMError(Exception):
    """Base error safe for application code to catch and inspect."""

    retryable = False

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class LLMTimeoutError(LLMError):
    retryable = True


class LLMRateLimitError(LLMError):
    retryable = True


class LLMAuthenticationError(LLMError):
    pass


class LLMUnavailableError(LLMError):
    retryable = True


class LLMInvalidResponseError(LLMError):
    pass


class LLMSchemaValidationError(LLMInvalidResponseError):
    pass


class LLMCapabilityError(LLMError):
    pass


class LLMConfigurationError(LLMError):
    pass
