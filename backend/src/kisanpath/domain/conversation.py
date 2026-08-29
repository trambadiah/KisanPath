"""Canonical conversation state; correctness never depends on raw chat replay."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.types import JsonValue

from kisanpath.domain.eligibility import SchemeEvaluation
from kisanpath.domain.profile import FarmerProfile, LanguageCode
from kisanpath.domain.verification import ClaimVerificationBatch


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


class PendingClarification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    affected_scheme_ids: tuple[str, ...] = ()
    affected_rule_ids: tuple[str, ...] = ()


class WorkflowTransition(BaseModel):
    """Operational audit data, never hidden chain-of-thought."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_stage: WorkflowStage
    to_stage: WorkflowStage
    occurred_at: datetime
    revision: int = Field(ge=1)
    trigger_message_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_aware_timestamp(self) -> WorkflowTransition:
        if self.occurred_at.tzinfo is None:
            raise ValueError("transition timestamp must be timezone-aware")
        return self


class ConversationState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    conversation_id: str = Field(min_length=1)
    preferred_language: LanguageCode
    current_profile: FarmerProfile = Field(default_factory=FarmerProfile)
    pending_confirmation: PendingConfirmation | None = None
    pending_clarification: PendingClarification | None = None
    workflow_stage: WorkflowStage = WorkflowStage.START
    candidate_scheme_ids: tuple[str, ...] = ()
    latest_evaluations: tuple[SchemeEvaluation, ...] = ()
    latest_claim_verifications: ClaimVerificationBatch = Field(
        default_factory=ClaimVerificationBatch
    )
    last_response_text: str | None = Field(default=None, min_length=1, max_length=20000)
    processed_message_ids: tuple[str, ...] = ()
    transitions: tuple[WorkflowTransition, ...] = ()
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
        if (
            self.pending_clarification
            and self.workflow_stage is not WorkflowStage.ASK_CLARIFICATION
        ):
            raise ValueError("pending clarification requires ASK_CLARIFICATION workflow stage")
        if self.pending_confirmation and self.pending_clarification:
            raise ValueError("only one pending user interaction is allowed")
        if len(self.processed_message_ids) != len(set(self.processed_message_ids)):
            raise ValueError("processed message IDs must be unique")
        if self.transitions:
            if self.transitions[-1].to_stage is not self.workflow_stage:
                raise ValueError("last transition must match current workflow stage")
            if self.transitions[-1].revision != self.revision:
                raise ValueError("last transition revision must match conversation revision")
            transition_revisions = [transition.revision for transition in self.transitions]
            if transition_revisions != list(range(1, self.revision + 1)):
                raise ValueError("workflow transition revisions must be contiguous")
        elif self.revision != 0:
            raise ValueError("a revised conversation requires workflow transitions")
        return self
