"""Canonical conversation state; correctness never depends on raw chat replay."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.types import JsonValue

from kisanpath.domain.eligibility import SchemeEvaluation
from kisanpath.domain.profile import FarmerProfile, LanguageCode


class WorkflowStage(StrEnum):
    START = "START"
    PARSE_INPUT = "PARSE_INPUT"
    UPDATE_PROFILE = "UPDATE_PROFILE"
    CONFIRM_VALUE = "CONFIRM_VALUE"
    ASK_CLARIFICATION = "ASK_CLARIFICATION"
    DISCOVER_SCHEMES = "DISCOVER_SCHEMES"
    EVALUATE_RULES = "EVALUATE_RULES"
    VERIFY_EVIDENCE = "VERIFY_EVIDENCE"
    COMPOSE_RESPONSE = "COMPOSE_RESPONSE"
    LOCALIZE = "LOCALIZE"
    SYNTHESIZE_AUDIO = "SYNTHESIZE_AUDIO"
    END = "END"


class PendingConfirmation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(min_length=1)
    proposed_value: JsonValue
    source_message_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)


class ConversationState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    conversation_id: str = Field(min_length=1)
    preferred_language: LanguageCode
    current_profile: FarmerProfile = Field(default_factory=FarmerProfile)
    pending_confirmation: PendingConfirmation | None = None
    workflow_stage: WorkflowStage = WorkflowStage.START
    candidate_scheme_ids: tuple[str, ...] = ()
    latest_evaluations: tuple[SchemeEvaluation, ...] = ()
    created_at: datetime
    updated_at: datetime
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> ConversationState:
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("conversation timestamps must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        if len(self.candidate_scheme_ids) != len(set(self.candidate_scheme_ids)):
            raise ValueError("candidate scheme IDs must be unique")
        evaluation_ids = [item.scheme_id for item in self.latest_evaluations]
        if len(evaluation_ids) != len(set(evaluation_ids)):
            raise ValueError("latest scheme evaluations must be unique")
        if self.pending_confirmation and self.workflow_stage is not WorkflowStage.CONFIRM_VALUE:
            raise ValueError("pending confirmation requires CONFIRM_VALUE workflow stage")
        return self
