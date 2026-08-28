"""Ollama native HTTP adapter."""

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
    map_finish_reason,
    normalize_error,
    openai_style_tool_call,
)
from kisanpath.llm.providers._http import http_client, require_object
from kisanpath.llm.structured import validate_structured_text

T = TypeVar("T", bound=BaseModel)


class OllamaAdapter:
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

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model_for(request),
            "messages": [
                {
                    **{"role": message.role.value, "content": message.content},
                    **(
                        {
                            "tool_calls": [
                                {
                                    "id": call.id,
                                    "type": "function",
                                    "function": {
                                        "name": call.name,
                                        "arguments": call.arguments,
                                    },
                                }
                                for call in message.tool_calls
                            ]
                        }
                        if message.tool_calls
                        else {}
                    ),
                }
                for message in request.messages
            ],
            "stream": False,
            "options": {"num_predict": request.max_output_tokens},
        }
        if request.temperature is not None:
            payload["options"]["temperature"] = request.temperature
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
                "/api/chat", json=payload, timeout=request.timeout_seconds
            )
            body = require_object(response)
        except Exception as exc:
            raise normalize_error(exc, provider=self.provider, model=model) from exc
        return body, (perf_counter() - started) * 1000

    def _response(self, raw: dict[str, Any], latency_ms: float, model: str) -> LLMResponse:
        message = raw.get("message")
        if not isinstance(message, dict):
            raise LLMInvalidResponseError(
                "Ollama response did not contain a message",
                provider=self.provider,
                model=model,
            )
        tools = tuple(
            openai_style_tool_call(tool, fallback_id=f"tool-{index}")
            for index, tool in enumerate(message.get("tool_calls") or [])
        )
        return LLMResponse(
            text=str(message.get("content") or ""),
            provider=self.provider,
            model=str(raw.get("model") or model),
            finish_reason=map_finish_reason(raw.get("done_reason")),
            usage=TokenUsage(
                input_tokens=int(raw.get("prompt_eval_count") or 0),
                output_tokens=int(raw.get("eval_count") or 0),
            ),
            latency_ms=latency_ms,
            tool_calls=tools,
            provider_metadata={
                "total_duration_ns": raw.get("total_duration"),
                "load_duration_ns": raw.get("load_duration"),
            },
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
        payload["format"] = request.output_schema.model_json_schema()
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
        payload = self._payload(request)
        payload["stream"] = True
        try:
            async with self._client.stream(
                "POST", "/api/chat", json=payload, timeout=request.timeout_seconds
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    message = chunk.get("message") or {}
                    if text := message.get("content"):
                        yield LLMStreamEvent(
                            event_type=StreamEventType.TEXT_DELTA, text_delta=str(text)
                        )
                    for index, tool in enumerate(message.get("tool_calls") or []):
                        yield LLMStreamEvent(
                            event_type=StreamEventType.TOOL_CALL,
                            tool_call=openai_style_tool_call(tool, fallback_id=f"tool-{index}"),
                        )
                    if chunk.get("done"):
                        usage = TokenUsage(
                            input_tokens=int(chunk.get("prompt_eval_count") or 0),
                            output_tokens=int(chunk.get("eval_count") or 0),
                        )
                        yield LLMStreamEvent(event_type=StreamEventType.USAGE, usage=usage)
                        yield LLMStreamEvent(
                            event_type=StreamEventType.END,
                            finish_reason=map_finish_reason(chunk.get("done_reason")),
                        )
        except Exception as exc:
            raise normalize_error(exc, provider=self.provider, model=model) from exc

    async def healthcheck(self) -> ProviderHealth:
        started = perf_counter()
        try:
            response = await self._client.get("/api/tags")
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


def create_ollama_client(
    alias: str, settings: ProviderSettings, environ: Mapping[str, str]
) -> OllamaAdapter:
    del environ
    if not settings.base_url:
        raise LLMConfigurationError("Ollama requires base_url", provider=alias)
    return OllamaAdapter(
        alias=alias,
        model=settings.model,
        client=http_client(settings),
        capabilities=settings.capabilities,
    )
