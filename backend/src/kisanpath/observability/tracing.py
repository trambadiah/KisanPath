"""OpenTelemetry-compatible tracing boundary without a mandatory exporter."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol


class Span(Protocol):
    def set_attribute(self, name: str, value: str | int | float | bool) -> None: ...
    def record_exception(self, exception: Exception) -> None: ...


class Tracer(Protocol):
    def start_span(
        self, name: str, *, attributes: Mapping[str, str | int | float | bool] | None = None
    ) -> AbstractAsyncContextManager[Span]: ...


class _NoopSpan:
    def set_attribute(self, name: str, value: str | int | float | bool) -> None:
        del name, value

    def record_exception(self, exception: Exception) -> None:
        del exception


class NoopTracer:
    @asynccontextmanager
    async def start_span(
        self, name: str, *, attributes: Mapping[str, str | int | float | bool] | None = None
    ) -> AsyncIterator[Span]:
        del name, attributes
        yield _NoopSpan()
