"""Protocol consumed by agents and application services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, TypeVar

from pydantic import BaseModel

from kisanpath.llm.models import (
    LLMRequest,
    LLMResponse,
    LLMStreamEvent,
    ProviderCapabilities,
    ProviderHealth,
    StructuredLLMRequest,
)

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def capabilities(self) -> ProviderCapabilities: ...

    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    async def generate_structured(self, request: StructuredLLMRequest[T]) -> T: ...

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamEvent]: ...

    async def healthcheck(self) -> ProviderHealth: ...
