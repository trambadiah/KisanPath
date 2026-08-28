"""Per-agent routing and explicit, reproducible fallback policy."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping
from enum import StrEnum
from typing import TypeVar

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

T = TypeVar("T", bound=BaseModel)
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
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._mode = mode
        self._environ = os.environ if environ is None else environ
        self._clients: dict[str, LLMClient] = {}

    def _client(self, alias: str) -> LLMClient:
        if alias not in self._clients:
            provider_settings = self._settings.providers[alias]
            self._clients[alias] = self._registry.create(
                alias, provider_settings, self._environ
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
        self,
        request: LLMRequest,
        route: RouteSettings,
        alias: str,
    ) -> LLMRequest:
        if request.model:
            return request
        if alias == route.provider and route.model:
            return request.model_copy(update={"model": route.model})
        return request.model_copy(update={"model": self._settings.providers[alias].model})

    @staticmethod
    def _ensure_capabilities(
        client: LLMClient,
        required: frozenset[Capability] | set[Capability],
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

    async def generate(self, request: LLMRequest, *, agent: str | None = None) -> LLMResponse:
        route = self._settings.route_for(agent)
        required = set(route.required_capabilities)
        if request.tools:
            required.add(Capability.NATIVE_TOOLS)
        last_error: Exception | None = None
        for index, alias in enumerate(self._aliases(route)):
            client = self._client(alias)
            self._ensure_capabilities(client, required)
            routed_request = self._with_route_model(request, route, alias)
            try:
                response = await client.generate(routed_request)
                if index:
                    metadata = {**response.provider_metadata, "fallback_from": route.provider}
                    response = response.model_copy(update={"provider_metadata": metadata})
                return response
            except _FALLBACK_ERRORS as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    async def generate_structured(
        self,
        request: StructuredLLMRequest[T],
        *,
        agent: str | None = None,
    ) -> T:
        route = self._settings.route_for(agent)
        required = set(route.required_capabilities)
        required.add(Capability.STRUCTURED_OUTPUT)
        last_error: Exception | None = None
        for alias in self._aliases(route):
            client = self._client(alias)
            self._ensure_capabilities(client, required)
            routed = request.model_copy(
                update={"request": self._with_route_model(request.request, route, alias)}
            )
            try:
                return await client.generate_structured(routed)
            except _FALLBACK_ERRORS as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    async def stream(
        self,
        request: LLMRequest,
        *,
        agent: str | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        route = self._settings.route_for(agent)
        required = set(route.required_capabilities)
        required.add(Capability.STREAMING)
        if request.tools:
            required.add(Capability.NATIVE_TOOLS)
        last_error: Exception | None = None
        for alias in self._aliases(route):
            client = self._client(alias)
            self._ensure_capabilities(client, required)
            routed_request = self._with_route_model(request, route, alias)
            emitted = False
            try:
                async for event in client.stream(routed_request):
                    emitted = True
                    yield event
                return
            except _FALLBACK_ERRORS as exc:
                if emitted:
                    raise
                last_error = exc
        assert last_error is not None
        raise last_error

    async def healthcheck(self, *, agent: str | None = None) -> ProviderHealth:
        return await self.client_for(agent).healthcheck()
