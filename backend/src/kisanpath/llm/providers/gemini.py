"""Google Gemini adapter using the google-genai async client."""

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


class GeminiAdapter:
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
        self._client = value(client, "aio", client)
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
    def _request_parts(request: LLMRequest) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        systems = [
            message.content for message in request.messages if message.role is MessageRole.SYSTEM
        ]
        contents: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role is MessageRole.SYSTEM:
                continue
            role = "model" if message.role is MessageRole.ASSISTANT else "user"
            if message.role is MessageRole.TOOL:
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "id": message.tool_call_id,
                                    "name": message.name or "tool",
                                    "response": {"result": message.content},
                                }
                            }
                        ],
                    }
                )
            elif message.tool_calls:
                parts: list[dict[str, Any]] = []
                if message.content:
                    parts.append({"text": message.content})
                parts.extend(
                    {
                        "function_call": {
                            "id": call.id,
                            "name": call.name,
                            "args": call.arguments,
                        }
                    }
                    for call in message.tool_calls
                )
                contents.append({"role": role, "parts": parts})
            else:
                contents.append({"role": role, "parts": [{"text": message.content}]})

        config: dict[str, Any] = {"max_output_tokens": request.max_output_tokens}
        if systems:
            config["system_instruction"] = "\n\n".join(systems)
        if request.temperature is not None:
            config["temperature"] = request.temperature
        if request.tools:
            config["tools"] = [
                {
                    "function_declarations": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters_json_schema": tool.input_schema,
                        }
                        for tool in request.tools
                    ]
                }
            ]
        return contents, config

    async def _generate(
        self, request: LLMRequest, *, config_extra: dict[str, Any] | None = None
    ) -> tuple[Any, float]:
        model = self._model_for(request)
        contents, config = self._request_parts(request)
        if config_extra:
            config.update(config_extra)
        started = perf_counter()
        try:
            async with asyncio.timeout(request.timeout_seconds):
                response = await self._client.models.generate_content(
                    model=model, contents=contents, config=config
                )
        except Exception as exc:
            raise normalize_error(exc, provider=self.provider, model=model) from exc
        return response, (perf_counter() - started) * 1000

    def _response(self, raw: Any, latency_ms: float, model: str) -> LLMResponse:
        candidates = value(raw, "candidates", []) or []
        finish = value(candidates[0], "finish_reason") if candidates else None
        tools: list[ToolCall] = []
        if candidates:
            content = value(candidates[0], "content", {}) or {}
            for index, part in enumerate(value(content, "parts", []) or []):
                call = value(part, "function_call")
                if call:
                    tools.append(
                        ToolCall(
                            id=str(value(call, "id", f"tool-{index}")),
                            name=str(value(call, "name", "unknown")),
                            arguments=dict(value(call, "args", {}) or {}),
                        )
                    )
        usage = value(raw, "usage_metadata", {}) or {}
        text = value(raw, "text")
        if text is None and not tools:
            raise LLMInvalidResponseError(
                "Gemini response did not contain text or tool calls",
                provider=self.provider,
                model=model,
            )
        return LLMResponse(
            text=str(text or ""),
            provider=self.provider,
            model=str(value(raw, "model_version", model) or model),
            finish_reason=map_finish_reason(finish),
            usage=TokenUsage(
                input_tokens=int(value(usage, "prompt_token_count", 0) or 0),
                output_tokens=int(value(usage, "candidates_token_count", 0) or 0),
                total_tokens=int(value(usage, "total_token_count", 0) or 0),
                cached_input_tokens=int(value(usage, "cached_content_token_count", 0) or 0),
            ),
            latency_ms=latency_ms,
            tool_calls=tuple(tools),
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = self._model_for(request)
        raw, latency = await self._generate(request)
        try:
            return self._response(raw, latency, model)
        except Exception as exc:
            if isinstance(exc, LLMInvalidResponseError):
                raise
            raise normalize_error(exc, provider=self.provider, model=model) from exc

    async def generate_structured(self, request: StructuredLLMRequest[T]) -> T:
        raw, latency = await self._generate(
            request.request,
            config_extra={
                "response_mime_type": "application/json",
                "response_json_schema": request.output_schema.model_json_schema(),
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
        contents, config = self._request_parts(request)
        try:
            async with asyncio.timeout(request.timeout_seconds):
                stream = await self._client.models.generate_content_stream(
                    model=model, contents=contents, config=config
                )
                async for chunk in stream:
                    text = value(chunk, "text", "") or ""
                    if text:
                        yield LLMStreamEvent(
                            event_type=StreamEventType.TEXT_DELTA, text_delta=str(text)
                        )
                    usage = value(chunk, "usage_metadata")
                    if usage:
                        yield LLMStreamEvent(
                            event_type=StreamEventType.USAGE,
                            usage=TokenUsage(
                                input_tokens=int(value(usage, "prompt_token_count", 0) or 0),
                                output_tokens=int(value(usage, "candidates_token_count", 0) or 0),
                                total_tokens=int(value(usage, "total_token_count", 0) or 0),
                            ),
                        )
                    candidates = value(chunk, "candidates", []) or []
                    finish = value(candidates[0], "finish_reason") if candidates else None
                    if finish:
                        yield LLMStreamEvent(
                            event_type=StreamEventType.END,
                            finish_reason=map_finish_reason(finish),
                        )
        except Exception as exc:
            raise normalize_error(exc, provider=self.provider, model=model) from exc

    async def healthcheck(self) -> ProviderHealth:
        started = perf_counter()
        try:
            await self._client.models.get(model=self._model)
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


def create_gemini_client(
    alias: str, settings: ProviderSettings, environ: Mapping[str, str]
) -> GeminiAdapter:
    api_key = settings.resolve_api_key(environ, required=True, alias=alias)
    try:
        from google import genai
    except ImportError as exc:
        raise LLMConfigurationError(
            "Install KisanPath with the 'gemini' provider extra", provider=alias
        ) from exc
    kwargs: dict[str, Any] = {"api_key": api_key}
    if settings.base_url:
        raise LLMConfigurationError(
            "Gemini base_url overrides are not supported; use the compatible adapter",
            provider=alias,
        )
    return GeminiAdapter(
        alias=alias,
        model=settings.model,
        client=genai.Client(**kwargs),
        capabilities=settings.capabilities,
    )
