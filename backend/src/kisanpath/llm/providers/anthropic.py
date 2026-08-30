"""Anthropic adapter using the async Messages API."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from time import perf_counter
from typing import Any, TypeVar

from pydantic import BaseModel

from kisanpath.llm.config import ProviderSettings
from kisanpath.llm.exceptions import LLMConfigurationError, LLMInvalidResponseError
from kisanpath.llm.models import (
    LLMRequest,
    LLMResponse,
    LLMStreamEvent,
    MessageRole,
    ProviderCapabilities,
    ProviderHealth,
    StreamEventType,
    StructuredLLMRequest,
    TokenUsage,
    ToolCall,
)
from kisanpath.llm.providers._common import map_finish_reason, normalize_error, value
from kisanpath.llm.structured import validate_structured_text

T = TypeVar("T", bound=BaseModel)


class AnthropicAdapter:
    def __init__(
        self,
        *,
        alias: str,
        model: str,
        client: Any,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self._alias = alias
        self._model = model
        self._client = client
        self._capabilities = capabilities or ProviderCapabilities(
            streaming=True,
            structured_output=True,
            native_tools=True,
            vision=False,
            system_messages=True,
        )

    @property
    def provider(self) -> str:
        return self._alias

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _model_for(self, request: LLMRequest) -> str:
        return request.model or self._model

    @staticmethod
    def _kwargs(request: LLMRequest, model: str) -> dict[str, Any]:
        systems = [m.content for m in request.messages if m.role is MessageRole.SYSTEM]
        messages: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role is MessageRole.SYSTEM:
                continue
            if message.role is MessageRole.TOOL:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_call_id,
                                "content": message.content,
                            }
                        ],
                    }
                )
            elif message.tool_calls:
                content: list[dict[str, Any]] = []
                if message.content:
                    content.append({"type": "text", "text": message.content})
                content.extend(
                    {
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.name,
                        "input": call.arguments,
                    }
                    for call in message.tool_calls
                )
                messages.append({"role": "assistant", "content": content})
            else:
                messages.append({"role": message.role.value, "content": message.content})
        result: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_output_tokens,
        }
        if systems:
            result["system"] = "\n\n".join(systems)
        if request.temperature is not None:
            result["temperature"] = request.temperature
        if request.tools:
            result["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }
                for tool in request.tools
            ]
        return result

    async def _create(self, request: LLMRequest, **extra: Any) -> tuple[Any, float]:
        model = self._model_for(request)
        started = perf_counter()
        try:
            async with asyncio.timeout(request.timeout_seconds):
                response = await self._client.messages.create(
                    **self._kwargs(request, model), **extra
                )
        except Exception as exc:
            raise normalize_error(exc, provider=self.provider, model=model) from exc
        return response, (perf_counter() - started) * 1000

    def _response(self, raw: Any, latency_ms: float, model: str) -> LLMResponse:
        content = value(raw, "content", []) or []
        texts: list[str] = []
        tools: list[ToolCall] = []
        for index, block in enumerate(content):
            block_type = value(block, "type")
            if block_type == "text":
                texts.append(str(value(block, "text", "")))
            elif block_type == "tool_use":
                tools.append(
                    ToolCall(
                        id=str(value(block, "id", f"tool-{index}")),
                        name=str(value(block, "name", "unknown")),
                        arguments=value(block, "input", {}) or {},
                    )
                )
        if not content:
            raise LLMInvalidResponseError(
                "Anthropic response did not contain content",
                provider=self.provider,
                model=model,
            )
        usage = value(raw, "usage", {}) or {}
        cache_read = int(value(usage, "cache_read_input_tokens", 0) or 0)
        return LLMResponse(
            text="".join(texts),
            provider=self.provider,
            model=str(value(raw, "model", model)),
            finish_reason=map_finish_reason(value(raw, "stop_reason")),
            usage=TokenUsage(
                input_tokens=int(value(usage, "input_tokens", 0) or 0),
                output_tokens=int(value(usage, "output_tokens", 0) or 0),
                cached_input_tokens=cache_read,
            ),
            latency_ms=latency_ms,
            tool_calls=tuple(tools),
            provider_metadata={"request_id": value(raw, "id")},
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = self._model_for(request)
        raw, latency = await self._create(request)
        try:
            return self._response(raw, latency, model)
        except Exception as exc:
            if isinstance(exc, LLMInvalidResponseError):
                raise
            raise normalize_error(exc, provider=self.provider, model=model) from exc

    async def generate_structured(self, request: StructuredLLMRequest[T]) -> T:
        raw, latency = await self._create(
            request.request,
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": request.output_schema.model_json_schema(),
                }
            },
        )
        model = self._model_for(request.request)
        try:
            response = self._response(raw, latency, model)
        except Exception as exc:
            if isinstance(exc, LLMInvalidResponseError):
                raise
            raise normalize_error(exc, provider=self.provider, model=model) from exc
        return validate_structured_text(
            response.text,
            request.output_schema,
            provider=self.provider,
            model=response.model,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        model = self._model_for(request)
        input_tokens = 0
        try:
            async with asyncio.timeout(request.timeout_seconds):
                stream = await self._client.messages.create(
                    **self._kwargs(request, model), stream=True
                )
                async for event in stream:
                    event_type = value(event, "type")
                    delta = value(event, "delta", {}) or {}
                    if event_type == "message_start":
                        message = value(event, "message", {}) or {}
                        usage = value(message, "usage", {}) or {}
                        input_tokens = int(value(usage, "input_tokens", 0) or 0)
                    elif (
                        event_type == "content_block_delta" and value(delta, "type") == "text_delta"
                    ):
                        yield LLMStreamEvent(
                            event_type=StreamEventType.TEXT_DELTA,
                            text_delta=str(value(delta, "text", "")),
                        )
                    elif event_type == "message_delta":
                        usage = value(event, "usage", {}) or {}
                        if usage:
                            yield LLMStreamEvent(
                                event_type=StreamEventType.USAGE,
                                usage=TokenUsage(
                                    input_tokens=input_tokens,
                                    output_tokens=int(value(usage, "output_tokens", 0) or 0),
                                ),
                            )
                        stop = value(delta, "stop_reason")
                        if stop:
                            yield LLMStreamEvent(
                                event_type=StreamEventType.END,
                                finish_reason=map_finish_reason(stop),
                            )
        except Exception as exc:
            raise normalize_error(exc, provider=self.provider, model=model) from exc

    async def healthcheck(self) -> ProviderHealth:
        started = perf_counter()
        try:
            await self._client.models.retrieve(self._model)
            return ProviderHealth(
                provider=self.provider,
                healthy=True,
                latency_ms=(perf_counter() - started) * 1000,
                model=self._model,
            )
        except Exception as exc:
            error = normalize_error(exc, provider=self.provider, model=self._model)
            return ProviderHealth(
                provider=self.provider,
                healthy=False,
                latency_ms=(perf_counter() - started) * 1000,
                model=self._model,
                detail=type(error).__name__,
            )


def create_anthropic_client(
    alias: str, settings: ProviderSettings, environ: Mapping[str, str]
) -> AnthropicAdapter:
    api_key = settings.resolve_api_key(environ, required=True, alias=alias)
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:
        raise LLMConfigurationError(
            "Install KisanPath with the 'anthropic' provider extra", provider=alias
        ) from exc
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": settings.timeout_seconds}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return AnthropicAdapter(
        alias=alias,
        model=settings.model,
        client=AsyncAnthropic(**kwargs),
        capabilities=settings.capabilities,
    )
