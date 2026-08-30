"""Shared normalization helpers used only by provider adapters."""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from kisanpath.llm.exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from kisanpath.llm.models import FinishReason, ToolCall


@dataclass
class OpenAIToolCallAccumulator:
    """Collect OpenAI-style streamed argument fragments into complete calls."""

    _calls: dict[int, dict[str, Any]] = field(default_factory=dict)

    def add(self, raw: Any, *, fallback_index: int) -> None:
        index = int(value(raw, "index", fallback_index) or 0)
        call = self._calls.setdefault(index, {"id": f"tool-{index}", "name": "", "arguments": ""})
        if call_id := value(raw, "id"):
            call["id"] = str(call_id)
        function = value(raw, "function", {}) or {}
        if name := value(function, "name"):
            call["name"] += str(name)
        arguments = value(function, "arguments")
        if isinstance(arguments, dict):
            call["arguments"] = arguments
        elif arguments:
            call["arguments"] += str(arguments)

    def drain(self) -> tuple[ToolCall, ...]:
        result = tuple(
            ToolCall(
                id=str(call["id"]),
                name=str(call["name"] or "unknown"),
                arguments=parse_tool_arguments(call["arguments"]),
            )
            for _, call in sorted(self._calls.items())
        )
        self._calls.clear()
        return result


def strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return an OpenAI-strict schema without mutating the canonical schema."""

    result = copy.deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            properties = node.get("properties")
            if node.get("type") == "object" and properties is None:
                properties = {}
                node["properties"] = properties
            if isinstance(properties, dict):
                node["additionalProperties"] = False
                node["required"] = list(properties)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(result)
    return result


def value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def normalize_error(exc: Exception, *, provider: str, model: str | None) -> LLMError:
    if isinstance(exc, LLMError):
        return exc
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException)):
        return LLMTimeoutError(f"{provider} request timed out", provider=provider, model=model)

    status = value(exc, "status_code") or value(exc, "code")
    response = value(exc, "response")
    if status is None and response is not None:
        status = value(response, "status_code")
    try:
        status_code = int(status) if status is not None else None
    except (TypeError, ValueError):
        status_code = None
    retry_after: float | None = None
    headers = value(response, "headers", {}) if response is not None else {}
    try:
        raw_retry_after = headers.get("retry-after") if headers else None
        retry_after = float(raw_retry_after) if raw_retry_after is not None else None
    except (TypeError, ValueError):
        retry_after = None

    class_name = type(exc).__name__.lower()
    if status_code in {401, 403} or "authentication" in class_name or "permission" in class_name:
        return LLMAuthenticationError(
            f"{provider} authentication failed",
            provider=provider,
            model=model,
            status_code=status_code,
            retry_after_seconds=retry_after,
        )
    if status_code == 429 or "ratelimit" in class_name or "rate_limit" in class_name:
        return LLMRateLimitError(
            f"{provider} rate limit exceeded",
            provider=provider,
            model=model,
            status_code=status_code,
            retry_after_seconds=retry_after,
        )
    if (
        status_code is not None
        and status_code >= 500
        or isinstance(exc, (httpx.NetworkError, ConnectionError))
        or "connection" in class_name
        or "unavailable" in class_name
    ):
        return LLMUnavailableError(
            f"{provider} is unavailable",
            provider=provider,
            model=model,
            status_code=status_code,
        )
    return LLMInvalidResponseError(
        f"{provider} request failed",
        provider=provider,
        model=model,
        status_code=status_code,
    )


def map_finish_reason(reason: Any) -> FinishReason:
    normalized = str(value(reason, "value", reason) or "").lower()
    if normalized in {"stop", "end_turn", "stop_sequence", "completed"}:
        return FinishReason.STOP
    if normalized in {"length", "max_tokens", "max_output_tokens", "incomplete"}:
        return FinishReason.LENGTH
    if normalized in {"tool_calls", "tool_use", "function_call"}:
        return FinishReason.TOOL_CALL
    if normalized in {"content_filter", "safety", "blocked", "refusal"}:
        return FinishReason.CONTENT_FILTER
    return FinishReason.UNKNOWN


def parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        result = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise LLMInvalidResponseError("Provider returned invalid tool arguments") from exc
    if not isinstance(result, dict):
        raise LLMInvalidResponseError("Provider tool arguments must be a JSON object")
    return result


def openai_style_tool_call(raw: Any, *, fallback_id: str) -> ToolCall:
    function = value(raw, "function", {})
    return ToolCall(
        id=str(value(raw, "id", fallback_id)),
        name=str(value(function, "name", "unknown")),
        arguments=parse_tool_arguments(value(function, "arguments", {})),
    )
