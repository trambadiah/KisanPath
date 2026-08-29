"""Transport-neutral commands, events, and results for the text workflow."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from kisanpath.domain.conversation import ConversationState, WorkflowStage
from kisanpath.domain.profile import LanguageCode


class TextMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    message_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=8000)
    language_hint: LanguageCode | None = None


class WorkflowEventType(StrEnum):
    PROFILE_UPDATED = "profile.updated"
    CONFIRMATION_REQUIRED = "confirmation.required"
    CLARIFICATION_REQUIRED = "clarification.required"
    DISCOVERY_STARTED = "discovery.started"
    DISCOVERY_COMPLETED = "discovery.completed"
    ELIGIBILITY_COMPLETED = "eligibility.completed"
    VERIFICATION_COMPLETED = "verification.completed"
    RESPONSE_READY = "response.ready"


class WorkflowEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: WorkflowEventType
    stage: WorkflowStage
    message: str = Field(min_length=1, max_length=1000)


class TextWorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: ConversationState
    response_text: str = Field(min_length=1, max_length=20000)
    events: tuple[WorkflowEvent, ...]
    idempotent_replay: bool = False
