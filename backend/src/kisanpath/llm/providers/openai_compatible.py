"""Generic OpenAI-compatible Chat Completions HTTP adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from time import perf_counter
from typing import Any, TypeVar

import httpx
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
)
from kisanpath.llm.providers._http import http_client, require_object
from kisanpath.llm.structured import validate_structured_text

T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleAdapter:
    def __init__(
        self,
        *,
        alias: str,
        model: str,
        client: httpx.AsyncClient,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self._alias = alias
        self._model = model
        self._client = client
        self._capabilities = capabilities or ProviderCapabilities(
            streaming=True,
            structured_output=False,
            native_tools=False,
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

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model_for(request),
            "messages": [
                ({
                    key: item
                    for key, item in {
                        "role": message.role.value,
                        "content": message.content,
                        "name": message.name,
                        "tool_call_id": message.tool_call_id,
                    }.items()
                    if item is not None
                } | ({
                    "tool_calls": [
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
                } if message.tool_calls else {}))
                for message in request.messages
            ],
            "max_tokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in request.tools
            ]
        return payload

    async def _post(
        self, request: LLMRequest, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], float]:
        model = self._model_for(request)
        started = perf_counter()
        try:
            response = await self._client.post(
                "/chat/completions", json=payload, timeout=request.timeout_seconds
            )
            body = require_object(response)
        except Exception as exc:
            raise normalize_error(exc, provider=self.provider, model=model) from exc
        return body, (perf_counter() - started) * 1000

    def _response(self, raw: dict[str, Any], latency_ms: float, model: str) -> LLMResponse:
        choices = raw.get("choices") or []
        if not choices:
            raise LLMInvalidResponseError(
                "Compatible endpoint response did not contain a choice",
                provider=self.provider,
                model=model,
            )
        choice = choices[0]
        message = choice.get("message") or {}
        tools = tuple(
            openai_style_tool_call(tool, fallback_id=f"tool-{index}")
            for index, tool in enumerate(message.get("tool_calls") or [])
        )
        usage = raw.get("usage") or {}
        return LLMResponse(
            text=str(message.get("content") or ""),
            provider=self.provider,
            model=str(raw.get("model") or model),
            finish_reason=map_finish_reason(choice.get("finish_reason")),
            usage=TokenUsage(
                input_tokens=int(usage.get("prompt_tokens") or 0),
                output_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
            ),
            latency_ms=latency_ms,
            tool_calls=tools,
            provider_metadata={"request_id": raw.get("id")},
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = self._model_for(request)
        raw, latency = await self._post(request, self._payload(request))
        try:
            return self._response(raw, latency, model)
        except Exception as exc:
            if isinstance(exc, LLMInvalidResponseError):
                raise
            raise normalize_error(exc, provider=self.provider, model=model) from exc

    async def generate_structured(self, request: StructuredLLMRequest[T]) -> T:
        payload = self._payload(request.request)
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": request.resolved_schema_name,
                "schema": strict_json_schema(request.output_schema.model_json_schema()),
                "strict": True,
            },
        }
        raw, latency = await self._post(request.request, payload)
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
        payload = self._payload(request)
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=payload, timeout=request.timeout_seconds
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        continue
                    chunk = json.loads(data)
                    usage = chunk.get("usage")
                    if usage:
                        yield LLMStreamEvent(
                            event_type=StreamEventType.USAGE,
                            usage=TokenUsage(
                                input_tokens=int(usage.get("prompt_tokens") or 0),
                                output_tokens=int(usage.get("completion_tokens") or 0),
                                total_tokens=int(usage.get("total_tokens") or 0),
                            ),
                        )
                    for choice in chunk.get("choices") or []:
                        delta = choice.get("delta") or {}
                        if text := delta.get("content"):
                            yield LLMStreamEvent(
                                event_type=StreamEventType.TEXT_DELTA, text_delta=str(text)
                            )
                        for index, tool in enumerate(delta.get("tool_calls") or []):
                            tool_calls.add(tool, fallback_index=index)
                        if finish := choice.get("finish_reason"):
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
            response = await self._client.get("/models")
            response.raise_for_status()
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


def create_openai_compatible_client(
    alias: str, settings: ProviderSettings, environ: Mapping[str, str]
) -> OpenAICompatibleAdapter:
    if not settings.base_url:
        raise LLMConfigurationError(
            "OpenAI-compatible providers require base_url", provider=alias
        )
    api_key = settings.resolve_api_key(environ, required=False, alias=alias)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    return OpenAICompatibleAdapter(
        alias=alias,
        model=settings.model,
        client=http_client(settings, headers=headers),
        capabilities=settings.capabilities,
    )
