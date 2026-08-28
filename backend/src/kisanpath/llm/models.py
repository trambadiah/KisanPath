"""Canonical, provider-independent LLM boundary models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(StrEnum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALL = "tool_call"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    UNKNOWN = "unknown"


class StreamEventType(StrEnum):
    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    USAGE = "usage"
    END = "end"


class Capability(StrEnum):
    STREAMING = "streaming"
    STRUCTURED_OUTPUT = "structured_output"
    NATIVE_TOOLS = "native_tools"
    VISION = "vision"
    SYSTEM_MESSAGES = "system_messages"


class ToolDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")
    description: str = Field(min_length=1)
    input_schema: dict[str, Any]


class ToolCall(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any]


class LLMMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()

    @model_validator(mode="after")
    def validate_tool_message(self) -> LLMMessage:
        if self.role is MessageRole.TOOL and (not self.tool_call_id or not self.name):
            raise ValueError("tool messages require tool_call_id and name")
        if self.role is not MessageRole.TOOL and self.tool_call_id is not None:
            raise ValueError("tool_call_id is only valid for tool messages")
        if self.tool_calls and self.role is not MessageRole.ASSISTANT:
            raise ValueError("tool_calls are only valid for assistant messages")
        return self


class LLMRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    messages: tuple[LLMMessage, ...] = Field(min_length=1)
    model: str | None = Field(default=None, min_length=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_output_tokens: int = Field(default=1024, gt=0)
    tools: tuple[ToolDefinition, ...] = ()
    timeout_seconds: float = Field(default=30.0, gt=0, le=600)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


StructuredT = TypeVar("StructuredT", bound=BaseModel)


class StructuredLLMRequest(BaseModel, Generic[StructuredT]):
    """A normal request plus the runtime schema that must validate its result."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    request: LLMRequest
    output_schema: type[StructuredT]
    schema_name: str | None = None

    @field_validator("output_schema")
    @classmethod
    def require_pydantic_model(cls, value: type[StructuredT]) -> type[StructuredT]:
        if not isinstance(value, type) or not issubclass(value, BaseModel):
            raise ValueError("output_schema must be a Pydantic BaseModel subclass")
        return value

    @property
    def resolved_schema_name(self) -> str:
        return self.schema_name or self.output_schema.__name__


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def populate_or_validate_total(self) -> TokenUsage:
        calculated = self.input_tokens + self.output_tokens
        if self.total_tokens == 0 and calculated:
            object.__setattr__(self, "total_tokens", calculated)
        elif self.total_tokens < calculated:
            raise ValueError("total_tokens cannot be less than input_tokens + output_tokens")
        return self


class ProviderCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    streaming: bool = True
    structured_output: bool = True
    native_tools: bool = False
    vision: bool = False
    system_messages: bool = True
    max_context_tokens: int | None = Field(default=None, gt=0)

    def supports(self, capability: Capability) -> bool:
        return bool(getattr(self, capability.value))


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    finish_reason: FinishReason = FinishReason.UNKNOWN
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = Field(ge=0)
    tool_calls: tuple[ToolCall, ...] = ()
    provider_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class LLMStreamEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: StreamEventType
    text_delta: str = ""
    tool_call: ToolCall | None = None
    usage: TokenUsage | None = None
    finish_reason: FinishReason | None = None


class ProviderHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    healthy: bool
    latency_ms: float = Field(ge=0)
    model: str | None = None
    detail: str | None = None
