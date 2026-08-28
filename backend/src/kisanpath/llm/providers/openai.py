"""OpenAI adapter using the async Chat Completions SDK surface."""

from __future__ import annotations

import asyncio
import json
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
    ProviderCapabilities,
    ProviderHealth,
    StreamEventType,
    StructuredLLMRequest,
    TokenUsage,
)
from kisanpath.llm.providers._common import (
    OpenAIToolCallAccumulator,
    map_finish_reason,
    normalize_error,
    openai_style_tool_call,
    strict_json_schema,
    value,
)
from kisanpath.llm.structured import validate_structured_text

T = TypeVar("T", bound=BaseModel)


class OpenAIAdapter:
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
    def _messages(request: LLMRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for message in request.messages:
            item: dict[str, Any] = {"role": message.role.value, "content": message.content}
            if message.name:
                item["name"] = message.name
            if message.tool_call_id:
                item["tool_call_id"] = message.tool_call_id
            if message.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                    for call in message.tool_calls
                ]
            messages.append(item)
        return messages

    def _kwargs(self, request: LLMRequest) -> dict[str, Any]:
        result: dict[str, Any] = {
            "model": self._model_for(request),
            "messages": self._messages(request),
            "max_completion_tokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            result["temperature"] = request.temperature
        if request.tools:
            result["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": strict_json_schema(tool.input_schema),
                        "strict": True,
                    },
                }
                for tool in request.tools
            ]
        return result

    async def _create(self, request: LLMRequest, **extra: Any) -> tuple[Any, float]:
        model = self._model_for(request)
        started = perf_counter()
        try:
            async with asyncio.timeout(request.timeout_seconds):
                response = await self._client.chat.completions.create(
                    **self._kwargs(request), **extra
                )
        except Exception as exc:
            raise normalize_error(exc, provider=self.provider, model=model) from exc
        return response, (perf_counter() - started) * 1000

    def _response(self, raw: Any, latency_ms: float, model: str) -> LLMResponse:
        choices = value(raw, "choices", [])
        if not choices:
            raise LLMInvalidResponseError(
                "OpenAI response did not contain a choice", provider=self.provider, model=model
            )
        choice = choices[0]
        message = value(choice, "message", {})
        raw_tool_calls = value(message, "tool_calls", []) or []
        tool_calls = tuple(
            openai_style_tool_call(tool, fallback_id=f"tool-{index}")
            for index, tool in enumerate(raw_tool_calls)
        )
        usage = value(raw, "usage", {}) or {}
        prompt_details = value(usage, "prompt_tokens_details", {}) or {}
        return LLMResponse(
            text=str(value(message, "content", "") or ""),
            provider=self.provider,
            model=str(value(raw, "model", model)),
            finish_reason=map_finish_reason(value(choice, "finish_reason")),
            usage=TokenUsage(
                input_tokens=int(value(usage, "prompt_tokens", 0) or 0),
                output_tokens=int(value(usage, "completion_tokens", 0) or 0),
                total_tokens=int(value(usage, "total_tokens", 0) or 0),
                cached_input_tokens=int(value(prompt_details, "cached_tokens", 0) or 0),
            ),
            latency_ms=latency_ms,
            tool_calls=tool_calls,
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
        schema = strict_json_schema(request.output_schema.model_json_schema())
        raw, latency = await self._create(
            request.request,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": request.resolved_schema_name,
                    "schema": schema,
                    "strict": True,
                },
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
        pending_finish = map_finish_reason(None)
        tool_calls = OpenAIToolCallAccumulator()
        try:
            async with asyncio.timeout(request.timeout_seconds):
                stream = await self._client.chat.completions.create(
                    **self._kwargs(request), stream=True, stream_options={"include_usage": True}
                )
                async for chunk in stream:
                    usage = value(chunk, "usage")
                    if usage is not None:
                        yield LLMStreamEvent(
                            event_type=StreamEventType.USAGE,
                            usage=TokenUsage(
                                input_tokens=int(value(usage, "prompt_tokens", 0) or 0),
                                output_tokens=int(value(usage, "completion_tokens", 0) or 0),
                                total_tokens=int(value(usage, "total_tokens", 0) or 0),
                            ),
                        )
                    for choice in value(chunk, "choices", []) or []:
                        delta = value(choice, "delta", {})
                        text = value(delta, "content", "") or ""
                        if text:
                            yield LLMStreamEvent(
                                event_type=StreamEventType.TEXT_DELTA, text_delta=str(text)
                            )
                        for index, tool in enumerate(value(delta, "tool_calls", []) or []):
                            tool_calls.add(tool, fallback_index=index)
                        finish = value(choice, "finish_reason")
                        if finish:
                            pending_finish = map_finish_reason(finish)
                            for tool_call in tool_calls.drain():
                                yield LLMStreamEvent(
                                    event_type=StreamEventType.TOOL_CALL,
                                    tool_call=tool_call,
                                )
                yield LLMStreamEvent(
                    event_type=StreamEventType.END,
                    finish_reason=pending_finish,
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


def create_openai_client(
    alias: str, settings: ProviderSettings, environ: Mapping[str, str]
) -> OpenAIAdapter:
    api_key = settings.resolve_api_key(environ, required=True, alias=alias)
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise LLMConfigurationError(
            "Install KisanPath with the 'openai' provider extra", provider=alias
        ) from exc
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": settings.timeout_seconds}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return OpenAIAdapter(
        alias=alias,
        model=settings.model,
        client=AsyncOpenAI(**kwargs),
        capabilities=settings.capabilities,
    )
