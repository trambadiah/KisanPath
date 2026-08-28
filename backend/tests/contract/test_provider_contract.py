from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import BaseModel

from kisanpath.llm.exceptions import (
    LLMAuthenticationError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMSchemaValidationError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from kisanpath.llm.models import (
    FinishReason,
    LLMMessage,
    LLMRequest,
    MessageRole,
    StreamEventType,
    StructuredLLMRequest,
    ToolDefinition,
)


class ExampleOutput(BaseModel):
    name: str
    count: int


def plain_request(*, tools: tuple[ToolDefinition, ...] = ()) -> LLMRequest:
    return LLMRequest(
        messages=(
            LLMMessage(role=MessageRole.SYSTEM, content="Be concise."),
            LLMMessage(role=MessageRole.USER, content="Help me."),
        ),
        model="contract-model",
        max_output_tokens=64,
        tools=tools,
    )


async def test_plain_generation_and_usage_are_normalized(adapter_case: object) -> None:
    response = await adapter_case.adapter.generate(plain_request())  # type: ignore[attr-defined]

    assert response.text == "hello farmer"
    assert response.model == "contract-model"
    assert response.finish_reason is FinishReason.STOP
    assert response.usage.input_tokens == 3
    assert response.usage.output_tokens == 2
    assert response.usage.total_tokens == 5


async def test_structured_generation_is_locally_validated(adapter_case: object) -> None:
    adapter_case.script.mode = "structured"  # type: ignore[attr-defined]
    result = await adapter_case.adapter.generate_structured(  # type: ignore[attr-defined]
        StructuredLLMRequest(request=plain_request(), output_schema=ExampleOutput)
    )

    assert result == ExampleOutput(name="Kisan", count=2)
    request_body = json.dumps(adapter_case.script.last_request, default=str)  # type: ignore[attr-defined]
    assert "count" in request_body
    if adapter_case.adapter.provider in {"openai", "openai_compatible"}:  # type: ignore[attr-defined]
        assert '"additionalProperties": false' in request_body


async def test_invalid_structured_generation_raises_internal_error(adapter_case: object) -> None:
    adapter_case.script.mode = "invalid"  # type: ignore[attr-defined]
    with pytest.raises(LLMSchemaValidationError):
        await adapter_case.adapter.generate_structured(  # type: ignore[attr-defined]
            StructuredLLMRequest(request=plain_request(), output_schema=ExampleOutput)
        )


async def test_rate_limit_is_normalized(adapter_case: object) -> None:
    adapter_case.script.mode = "rate_limit"  # type: ignore[attr-defined]
    with pytest.raises(LLMRateLimitError) as error:
        await adapter_case.adapter.generate(plain_request())  # type: ignore[attr-defined]
    assert error.value.retryable is True


async def test_authentication_error_is_normalized(adapter_case: object) -> None:
    adapter_case.script.mode = "authentication"  # type: ignore[attr-defined]
    with pytest.raises(LLMAuthenticationError) as error:
        await adapter_case.adapter.generate(plain_request())  # type: ignore[attr-defined]
    assert error.value.retryable is False


async def test_unavailability_is_normalized(adapter_case: object) -> None:
    adapter_case.script.mode = "unavailable"  # type: ignore[attr-defined]
    with pytest.raises(LLMUnavailableError) as error:
        await adapter_case.adapter.generate(plain_request())  # type: ignore[attr-defined]
    assert error.value.retryable is True


async def test_timeout_is_normalized(adapter_case: object) -> None:
    adapter_case.script.mode = "timeout"  # type: ignore[attr-defined]
    with pytest.raises(LLMTimeoutError):
        await adapter_case.adapter.generate(plain_request())  # type: ignore[attr-defined]


async def test_malformed_provider_payload_is_normalized(adapter_case: object) -> None:
    adapter_case.script.mode = "malformed"  # type: ignore[attr-defined]
    with pytest.raises(LLMInvalidResponseError):
        await adapter_case.adapter.generate(plain_request())  # type: ignore[attr-defined]


async def test_cancellation_is_never_swallowed(adapter_case: object) -> None:
    adapter_case.script.mode = "cancelled"  # type: ignore[attr-defined]
    with pytest.raises(asyncio.CancelledError):
        await adapter_case.adapter.generate(plain_request())  # type: ignore[attr-defined]


async def test_stream_events_are_normalized(adapter_case: object) -> None:
    events = [event async for event in adapter_case.adapter.stream(plain_request())]  # type: ignore[attr-defined]

    text = "".join(event.text_delta for event in events)
    assert text == "hello farmer"
    assert any(event.event_type is StreamEventType.END for event in events)
    assert any(event.event_type is StreamEventType.USAGE for event in events)


async def test_tool_calls_are_normalized(adapter_case: object) -> None:
    adapter_case.script.mode = "tool"  # type: ignore[attr-defined]
    tool = ToolDefinition(
        name="lookup",
        description="Look up an approved scheme.",
        input_schema={
            "type": "object",
            "properties": {"scheme": {"type": "string"}},
            "required": ["scheme"],
        },
    )
    response = await adapter_case.adapter.generate(plain_request(tools=(tool,)))  # type: ignore[attr-defined]

    assert response.finish_reason is FinishReason.TOOL_CALL
    assert response.tool_calls[0].name == "lookup"
    assert response.tool_calls[0].arguments == {"scheme": "demo"}
    request_body = json.dumps(adapter_case.script.last_request, default=str)  # type: ignore[attr-defined]
    assert "lookup" in request_body


async def test_healthcheck_is_normalized(adapter_case: object) -> None:
    health = await adapter_case.adapter.healthcheck()  # type: ignore[attr-defined]

    assert health.healthy is True
    assert health.provider == adapter_case.adapter.provider  # type: ignore[attr-defined]
