"""Evidence-verification result models for user-visible claims."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VerificationStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    UNCERTAIN = "uncertain"


class ClaimImportance(StrEnum):
    CONSEQUENTIAL = "consequential"
    INFORMATIONAL = "informational"


class ClaimVerification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    importance: ClaimImportance
    status: VerificationStatus
    source_ref_ids: tuple[str, ...] = ()
    derived_rule_ids: tuple[str, ...] = ()
    explanation: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_evidence(self) -> ClaimVerification:
        if self.status is VerificationStatus.SUPPORTED:
            if not self.source_ref_ids and not self.derived_rule_ids:
                raise ValueError("supported claims require a source or deterministic rule")
        if self.status is VerificationStatus.UNSUPPORTED:
            if self.source_ref_ids or self.derived_rule_ids:
                raise ValueError("unsupported claims cannot cite supporting evidence")
        return self


class ClaimVerificationBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claims: tuple[ClaimVerification, ...] = ()

    @model_validator(mode="after")
    def validate_claim_ids(self) -> ClaimVerificationBatch:
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim IDs must be unique")
        return self

    @property
    def publishable(self) -> bool:
        return all(
            claim.importance is not ClaimImportance.CONSEQUENTIAL
            or claim.status is VerificationStatus.SUPPORTED
            for claim in self.claims
        )
