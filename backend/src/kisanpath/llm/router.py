"""Per-agent routing with bounded transient retries and explicit fallback policy."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from enum import StrEnum
from time import perf_counter
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from kisanpath.llm.base import LLMClient
from kisanpath.llm.config import LLMSettings, RouteSettings
from kisanpath.llm.exceptions import (
    LLMCapabilityError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from kisanpath.llm.models import (
    Capability,
    LLMRequest,
    LLMResponse,
    LLMStreamEvent,
    ProviderHealth,
    StructuredLLMRequest,
)
from kisanpath.llm.registry import ProviderRegistry
from kisanpath.observability.context import bind_context
from kisanpath.observability.metrics import MetricsSink, NoopMetrics
from kisanpath.observability.tracing import NoopTracer, Tracer

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")
_FALLBACK_ERRORS = (LLMTimeoutError, LLMRateLimitError, LLMUnavailableError)


class RouterMode(StrEnum):
    PRODUCTION = "production"
    EVALUATION = "evaluation"


class LLMRouter:
    def __init__(
        self,
        settings: LLMSettings,
        registry: ProviderRegistry,
        *,
        mode: RouterMode = RouterMode.PRODUCTION,
        environ: Mapping[str, str] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        metrics: MetricsSink | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._mode = mode
        self._environ = os.environ if environ is None else environ
        self._clients: dict[str, LLMClient] = {}
        self._sleep = sleep
        self._metrics = metrics or NoopMetrics()
        self._tracer = tracer or NoopTracer()

    def _client(self, alias: str) -> LLMClient:
        if alias not in self._clients:
            self._clients[alias] = self._registry.create(
                alias, self._settings.providers[alias], self._environ
            )
        return self._clients[alias]

    def _fallback_allowed(self) -> bool:
        if self._mode is RouterMode.EVALUATION:
            return self._settings.evaluation_fallback_enabled
        return self._settings.fallback_enabled

    def _aliases(self, route: RouteSettings) -> tuple[str, ...]:
        if self._fallback_allowed():
            return (route.provider, *route.fallbacks)
        return (route.provider,)

    def _with_route_model(
        self, request: LLMRequest, route: RouteSettings, alias: str
    ) -> LLMRequest:
        if request.model:
            return request
        if alias == route.provider and route.model:
            return request.model_copy(update={"model": route.model})
        return request.model_copy(update={"model": self._settings.providers[alias].model})

    @staticmethod
    def _ensure_capabilities(
        client: LLMClient, required: frozenset[Capability] | set[Capability]
    ) -> None:
        missing = sorted(cap.value for cap in required if not client.capabilities.supports(cap))
        if missing:
            raise LLMCapabilityError(
                f"Provider '{client.provider}' lacks required capabilities: {missing}",
                provider=client.provider,
            )

    def client_for(self, agent: str | None = None) -> LLMClient:
        route = self._settings.route_for(agent)
        client = self._client(route.provider)
        self._ensure_capabilities(client, route.required_capabilities)
        return client

    def _delay(self, attempt: int, error: Exception) -> float:
        configured: float = min(
            float(self._settings.retry.initial_backoff_seconds) * (2 ** (attempt - 1)),
            float(self._settings.retry.max_backoff_seconds),
        )
        raw_provider_delay = getattr(error, "retry_after_seconds", None)
        provider_delay = (
            float(raw_provider_delay) if isinstance(raw_provider_delay, (int, float)) else 0
        )
        return float(
            min(
                max(configured, provider_delay),
                float(self._settings.retry.max_backoff_seconds),
            )
        )

    async def _call_with_retries(
        self,
        operation: Callable[[], Awaitable[R]],
        *,
        provider: str,
        model: str,
        agent: str | None,
        operation_name: str,
    ) -> tuple[R, int]:
        last_error: Exception | None = None
        labels = {"provider": provider, "model": model, "agent": agent or "default"}
        for attempt in range(1, self._settings.retry.max_attempts + 1):
            tokens = bind_context(llm_run_id=str(uuid4()))
            started = perf_counter()
            try:
                async with self._tracer.start_span(
                    f"llm.{operation_name}",
                    attributes={**labels, "attempt": attempt},
                ) as span:
                    try:
                        result = await operation()
                    except _FALLBACK_ERRORS as exc:
                        span.record_exception(exc)
                        raise
                self._metrics.increment(
                    "kisanpath_llm_requests_total",
                    labels={**labels, "outcome": "success"},
                )
                self._metrics.observe(
                    "kisanpath_llm_request_duration_ms",
                    (perf_counter() - started) * 1000,
                    labels=labels,
                )
                return result, attempt
            except _FALLBACK_ERRORS as exc:
                last_error = exc
                self._metrics.increment(
                    "kisanpath_llm_requests_total",
                    labels={**labels, "outcome": type(exc).__name__},
                )
                if attempt < self._settings.retry.max_attempts:
                    self._metrics.increment(
                        "kisanpath_llm_retries_total",
                        labels={"provider": provider, "reason": type(exc).__name__},
                    )
                    await self._sleep(self._delay(attempt, exc))
            finally:
                tokens.reset()
        assert last_error is not None
        raise last_error

    async def generate(self, request: LLMRequest, *, agent: str | None = None) -> LLMResponse:
        route = self._settings.route_for(agent)
        required = set(route.required_capabilities)
        if request.tools:
            required.add(Capability.NATIVE_TOOLS)
        last_error: Exception | None = None
        aliases = self._aliases(route)
        for index, alias in enumerate(aliases):
            client = self._client(alias)
            self._ensure_capabilities(client, required)
            routed = self._with_route_model(request, route, alias)

            async def invoke(
                client: LLMClient = client,
                routed: LLMRequest = routed,
            ) -> LLMResponse:
                return await client.generate(routed)

            try:
                response, attempts = await self._call_with_retries(
                    invoke,
                    provider=alias,
                    model=routed.model or "default",
                    agent=agent,
                    operation_name="generate",
                )
                metadata = {**response.provider_metadata, "attempts": attempts}
                if index:
                    metadata["fallback_from"] = route.provider
                return response.model_copy(update={"provider_metadata": metadata})
            except _FALLBACK_ERRORS as exc:
                last_error = exc
                if index + 1 < len(aliases):
                    self._metrics.increment(
                        "kisanpath_llm_fallbacks_total",
                        labels={"provider": alias, "reason": type(exc).__name__},
                    )
        assert last_error is not None
        raise last_error

    async def generate_structured(
        self,
        request: StructuredLLMRequest[T],
        *,
        agent: str | None = None,
    ) -> T:
        route = self._settings.route_for(agent)
        required = set(route.required_capabilities) | {Capability.STRUCTURED_OUTPUT}
        last_error: Exception | None = None
        aliases = self._aliases(route)
        for index, alias in enumerate(aliases):
            client = self._client(alias)
            self._ensure_capabilities(client, required)
            routed = request.model_copy(
                update={"request": self._with_route_model(request.request, route, alias)}
            )

            async def invoke_structured(
                client: LLMClient = client,
                routed: StructuredLLMRequest[T] = routed,
            ) -> T:
                return await client.generate_structured(routed)

            try:
                result, _attempts = await self._call_with_retries(
                    invoke_structured,
                    provider=alias,
                    model=routed.request.model or "default",
                    agent=agent,
                    operation_name="generate_structured",
                )
                return result
            except _FALLBACK_ERRORS as exc:
                last_error = exc
                if index + 1 < len(aliases):
                    self._metrics.increment(
                        "kisanpath_llm_fallbacks_total",
                        labels={"provider": alias, "reason": type(exc).__name__},
                    )
        assert last_error is not None
        raise last_error

    async def stream(
        self,
        request: LLMRequest,
        *,
        agent: str | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        route = self._settings.route_for(agent)
        required = set(route.required_capabilities) | {Capability.STREAMING}
        if request.tools:
            required.add(Capability.NATIVE_TOOLS)
        last_error: Exception | None = None
        aliases = self._aliases(route)
        for index, alias in enumerate(aliases):
            client = self._client(alias)
            self._ensure_capabilities(client, required)
            routed = self._with_route_model(request, route, alias)
            for attempt in range(1, self._settings.retry.max_attempts + 1):
                emitted = False
                tokens = bind_context(llm_run_id=str(uuid4()))
                try:
                    async with self._tracer.start_span(
                        "llm.stream",
                        attributes={
                            "provider": alias,
                            "model": routed.model or "default",
                            "agent": agent or "default",
                            "attempt": attempt,
                        },
                    ):
                        async for event in client.stream(routed):
                            emitted = True
                            yield event
                    self._metrics.increment(
                        "kisanpath_llm_requests_total",
                        labels={
                            "provider": alias,
                            "model": routed.model or "default",
                            "agent": agent or "default",
                            "outcome": "success",
                        },
                    )
                    return
                except _FALLBACK_ERRORS as exc:
                    if emitted:
                        raise
                    last_error = exc
                    if attempt < self._settings.retry.max_attempts:
                        self._metrics.increment(
                            "kisanpath_llm_retries_total",
                            labels={"provider": alias, "reason": type(exc).__name__},
                        )
                        await self._sleep(self._delay(attempt, exc))
                finally:
                    tokens.reset()
            if index + 1 < len(aliases):
                self._metrics.increment(
                    "kisanpath_llm_fallbacks_total",
                    labels={"provider": alias, "reason": type(last_error).__name__},
                )
        assert last_error is not None
        raise last_error

    async def healthcheck(self, *, agent: str | None = None) -> ProviderHealth:
        return await self.client_for(agent).healthcheck()
