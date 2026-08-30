from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import pytest

from kisanpath.llm.config import LLMSettings, ProviderSettings, RetrySettings, RouteSettings
from kisanpath.llm.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMUnavailableError,
)
from kisanpath.llm.models import (
    FinishReason,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMStreamEvent,
    MessageRole,
    ProviderCapabilities,
    ProviderHealth,
    StreamEventType,
)
from kisanpath.llm.registry import ProviderRegistry
from kisanpath.llm.router import LLMRouter


@dataclass
class OutageClient:
    provider: str
    failures: list[Exception] = field(default_factory=list)
    emitted_then_failure: bool = False
    calls: int = 0
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return LLMResponse(
            text=self.provider,
            provider=self.provider,
            model=request.model or "test",
            finish_reason=FinishReason.STOP,
            latency_ms=1,
        )

    async def generate_structured(self, request: object) -> object:
        raise NotImplementedError

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        self.calls += 1
        if self.emitted_then_failure:
            yield LLMStreamEvent(event_type=StreamEventType.TEXT_DELTA, text_delta="partial")
            raise LLMUnavailableError("stream dropped")
        if self.failures:
            raise self.failures.pop(0)
        yield LLMStreamEvent(event_type=StreamEventType.END, finish_reason=FinishReason.STOP)

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider, healthy=True, latency_ms=1)


def build(primary: OutageClient, fallback: OutageClient, delays: list[float]) -> LLMRouter:
    settings = LLMSettings(
        default=RouteSettings(provider="primary", fallbacks=("fallback",)),
        providers={
            "primary": ProviderSettings(adapter="test", model="primary-model"),
            "fallback": ProviderSettings(adapter="test", model="fallback-model"),
        },
        retry=RetrySettings(
            max_attempts=2,
            initial_backoff_seconds=0.1,
            max_backoff_seconds=0.5,
        ),
    )
    registry = ProviderRegistry()
    registry.register(
        "test", lambda alias, _settings, _env: primary if alias == "primary" else fallback
    )

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    return LLMRouter(settings, registry, environ={}, sleep=record_sleep)


def request() -> LLMRequest:
    return LLMRequest(messages=(LLMMessage(role=MessageRole.USER, content="synthetic"),))


async def test_transient_outage_retries_primary_before_fallback() -> None:
    primary = OutageClient("primary", failures=[LLMUnavailableError("down")])
    fallback = OutageClient("fallback")
    delays: list[float] = []

    response = await build(primary, fallback, delays).generate(request())

    assert response.provider == "primary"
    assert response.provider_metadata["attempts"] == 2
    assert primary.calls == 2
    assert fallback.calls == 0
    assert delays == [0.1]


async def test_rate_limit_retry_after_is_bounded_then_falls_back() -> None:
    primary = OutageClient(
        "primary",
        failures=[
            LLMRateLimitError("limited", retry_after_seconds=30),
            LLMRateLimitError("limited", retry_after_seconds=30),
        ],
    )
    fallback = OutageClient("fallback")
    delays: list[float] = []

    response = await build(primary, fallback, delays).generate(request())

    assert response.provider == "fallback"
    assert response.provider_metadata["fallback_from"] == "primary"
    assert delays == [0.5]


async def test_authentication_failure_is_not_retried_or_hidden_by_fallback() -> None:
    primary = OutageClient("primary", failures=[LLMAuthenticationError("bad key")])
    fallback = OutageClient("fallback")

    with pytest.raises(LLMAuthenticationError):
        await build(primary, fallback, []).generate(request())

    assert primary.calls == 1
    assert fallback.calls == 0


async def test_stream_never_retries_or_falls_back_after_emitting_content() -> None:
    primary = OutageClient("primary", emitted_then_failure=True)
    fallback = OutageClient("fallback")
    events: list[LLMStreamEvent] = []

    with pytest.raises(LLMUnavailableError):
        async for event in build(primary, fallback, []).stream(request()):
            events.append(event)

    assert [event.text_delta for event in events] == ["partial"]
    assert primary.calls == 1
    assert fallback.calls == 0
