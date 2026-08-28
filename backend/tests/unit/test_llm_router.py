from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import TypeVar

import pytest
from pydantic import BaseModel

from kisanpath.llm.base import LLMClient
from kisanpath.llm.config import LLMSettings, ProviderSettings, RouteSettings
from kisanpath.llm.exceptions import (
    LLMCapabilityError,
    LLMConfigurationError,
    LLMSchemaValidationError,
    LLMUnavailableError,
)
from kisanpath.llm.models import (
    Capability,
    FinishReason,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMStreamEvent,
    MessageRole,
    ProviderCapabilities,
    ProviderHealth,
    StructuredLLMRequest,
)
from kisanpath.llm.registry import ProviderRegistry
from kisanpath.llm.router import LLMRouter, RouterMode

T = TypeVar("T", bound=BaseModel)


class Output(BaseModel):
    value: str


@dataclass
class StubClient:
    provider: str
    failure: Exception | None = None
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    models_seen: list[str | None] = field(default_factory=list)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.models_seen.append(request.model)
        if self.failure:
            raise self.failure
        return LLMResponse(
            text=self.provider,
            provider=self.provider,
            model=request.model or "default",
            finish_reason=FinishReason.STOP,
            latency_ms=0,
        )

    async def generate_structured(self, request: StructuredLLMRequest[T]) -> T:
        self.models_seen.append(request.request.model)
        if self.failure:
            raise self.failure
        return request.output_schema.model_validate({"value": self.provider})

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        self.models_seen.append(request.model)
        if self.failure:
            raise self.failure
        if False:
            yield LLMStreamEvent.model_construct()

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider, healthy=True, latency_ms=0)


def build_router(
    clients: Mapping[str, StubClient],
    *,
    mode: RouterMode = RouterMode.PRODUCTION,
    evaluation_fallback_enabled: bool = False,
) -> LLMRouter:
    providers = {
        alias: ProviderSettings(adapter=alias, model=f"{alias}-model") for alias in clients
    }
    settings = LLMSettings(
        default=RouteSettings(
            provider="primary", model="route-model", fallbacks=("fallback",)
        ),
        agents={"profile": RouteSettings(provider="fallback")},
        providers=providers,
        fallback_enabled=True,
        evaluation_fallback_enabled=evaluation_fallback_enabled,
    )
    registry = ProviderRegistry()
    for alias, client in clients.items():
        registry.register(alias, lambda _alias, _settings, _env, client=client: client)
    return LLMRouter(settings, registry, mode=mode, environ={})


def request() -> LLMRequest:
    return LLMRequest(messages=(LLMMessage(role=MessageRole.USER, content="hello"),))


async def test_per_agent_route_changes_provider_without_agent_code() -> None:
    clients = {"primary": StubClient("primary"), "fallback": StubClient("fallback")}
    router = build_router(clients)

    response = await router.generate(request(), agent="profile")

    assert response.provider == "fallback"
    assert clients["fallback"].models_seen == ["fallback-model"]


async def test_transient_failure_falls_back_with_provider_specific_model() -> None:
    clients = {
        "primary": StubClient("primary", LLMUnavailableError("down")),
        "fallback": StubClient("fallback"),
    }
    router = build_router(clients)

    response = await router.generate(request())

    assert response.provider == "fallback"
    assert response.provider_metadata["fallback_from"] == "primary"
    assert clients["primary"].models_seen == ["route-model"]
    assert clients["fallback"].models_seen == ["fallback-model"]


async def test_evaluation_mode_does_not_fallback_by_default() -> None:
    clients = {
        "primary": StubClient("primary", LLMUnavailableError("down")),
        "fallback": StubClient("fallback"),
    }
    router = build_router(clients, mode=RouterMode.EVALUATION)

    with pytest.raises(LLMUnavailableError):
        await router.generate(request())
    assert clients["fallback"].models_seen == []


async def test_evaluation_fallback_can_be_enabled_explicitly() -> None:
    clients = {
        "primary": StubClient("primary", LLMUnavailableError("down")),
        "fallback": StubClient("fallback"),
    }
    router = build_router(
        clients, mode=RouterMode.EVALUATION, evaluation_fallback_enabled=True
    )

    response = await router.generate(request())
    assert response.provider == "fallback"


async def test_schema_failure_never_triggers_fallback() -> None:
    clients = {
        "primary": StubClient("primary", LLMSchemaValidationError("invalid")),
        "fallback": StubClient("fallback"),
    }
    router = build_router(clients)

    with pytest.raises(LLMSchemaValidationError):
        await router.generate_structured(
            StructuredLLMRequest(request=request(), output_schema=Output)
        )
    assert clients["fallback"].models_seen == []


async def test_required_capability_is_checked_before_call() -> None:
    clients = {
        "primary": StubClient(
            "primary", capabilities=ProviderCapabilities(structured_output=False)
        ),
        "fallback": StubClient("fallback"),
    }
    providers = {
        alias: ProviderSettings(adapter=alias, model=f"{alias}-model") for alias in clients
    }
    settings = LLMSettings(
        default=RouteSettings(
            provider="primary", required_capabilities=frozenset({Capability.STRUCTURED_OUTPUT})
        ),
        providers=providers,
    )
    registry = ProviderRegistry()
    for alias, client in clients.items():
        registry.register(alias, lambda _alias, _settings, _env, client=client: client)
    router = LLMRouter(settings, registry, environ={})

    with pytest.raises(LLMCapabilityError):
        await router.generate(request())


def test_duplicate_registry_adapter_is_rejected() -> None:
    registry = ProviderRegistry()

    def factory(
        _alias: str, _settings: ProviderSettings, _env: Mapping[str, str]
    ) -> LLMClient:
        return StubClient("test")

    registry.register("test", factory)
    with pytest.raises(LLMConfigurationError):
        registry.register("test", factory)
