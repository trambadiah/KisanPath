from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from kisanpath.llm.exceptions import LLMSchemaValidationError
from kisanpath.llm.models import (
    LLMMessage,
    LLMRequest,
    MessageRole,
    StructuredLLMRequest,
    TokenUsage,
    ToolCall,
)
from kisanpath.llm.structured import validate_structured_text


class Result(BaseModel):
    value: int


def test_request_requires_at_least_one_message() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(messages=())


def test_tool_message_requires_call_id() -> None:
    with pytest.raises(ValidationError):
        LLMMessage(role=MessageRole.TOOL, content="result")


def test_tool_message_preserves_provider_independent_identity() -> None:
    message = LLMMessage(
        role=MessageRole.TOOL,
        content='{"eligible":true}',
        name="lookup",
        tool_call_id="call-1",
    )
    assert message.name == "lookup"


def test_assistant_message_can_preserve_tool_call_history() -> None:
    message = LLMMessage(
        role=MessageRole.ASSISTANT,
        content="",
        tool_calls=(ToolCall(id="call-1", name="lookup", arguments={"id": 1}),),
    )
    assert message.tool_calls[0].name == "lookup"


def test_user_message_cannot_claim_tool_calls() -> None:
    with pytest.raises(ValidationError):
        LLMMessage(
            role=MessageRole.USER,
            content="invalid",
            tool_calls=(ToolCall(id="call-1", name="lookup", arguments={}),),
        )


def test_usage_populates_total() -> None:
    usage = TokenUsage(input_tokens=3, output_tokens=4)
    assert usage.total_tokens == 7


def test_usage_rejects_inconsistent_total() -> None:
    with pytest.raises(ValidationError):
        TokenUsage(input_tokens=3, output_tokens=4, total_tokens=6)


def test_structured_request_exposes_runtime_schema() -> None:
    request = StructuredLLMRequest(
        request=LLMRequest(
            messages=(LLMMessage(role=MessageRole.USER, content="return JSON"),)
        ),
        output_schema=Result,
    )
    assert request.resolved_schema_name == "Result"


def test_structured_validation_accepts_json_fence() -> None:
    result = validate_structured_text(
        '```json\n{"value": 7}\n```', Result, provider="fake", model="fake-model"
    )
    assert result.value == 7


def test_structured_validation_maps_schema_error() -> None:
    with pytest.raises(LLMSchemaValidationError):
        validate_structured_text(
            '{"value":"unknown"}', Result, provider="fake", model="fake-model"
        )
