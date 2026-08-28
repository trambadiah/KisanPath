"""Typed records for the untrusted-to-published ingestion lifecycle."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kisanpath.domain.scheme import PublicationState, Scheme, SourceReviewStatus
from kisanpath.persistence.models import (
    ParsedDocumentChunk,
    PublishedSchemeVersion,
    SourceDocumentRecord,
)


class IngestionState(StrEnum):
    RAW = "raw"
    PARSED = "parsed"
    AUTO_EXTRACTED = "auto_extracted"
    VALIDATED = "validated"
    HUMAN_REVIEWED = "human_reviewed"
    PUBLISHED = "published"
    RETIRED = "retired"


class ActorKind(StrEnum):
    SYSTEM = "system"
    HUMAN = "human"


class TransitionActor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_id: str = Field(min_length=1)
    kind: ActorKind


class IngestionEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    from_state: IngestionState | None
    to_state: IngestionState
    actor: TransitionActor
    occurred_at: datetime
    revision: int = Field(ge=0)
    note: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def require_aware_timestamp(self) -> IngestionEvent:
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return self


class ParsedDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    parsed_at: datetime
    chunks: tuple[ParsedDocumentChunk, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_chunks(self) -> ParsedDocument:
        if self.parsed_at.tzinfo is None:
            raise ValueError("parsed_at must be timezone-aware")
        if any(chunk.document_id != self.document_id for chunk in self.chunks):
            raise ValueError("parsed chunks must belong to their containing document")
        chunk_ids = [chunk.chunk_id for chunk in self.chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("parsed chunk IDs must be unique")
        source_ids = [chunk.source_ref_id for chunk in self.chunks]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("parsed chunk source reference IDs must be unique")
        ordinals = [chunk.ordinal for chunk in self.chunks]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("parsed chunk ordinals must be unique")
        return self


class ExtractionMethod(StrEnum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class ExtractedSchemeCandidate(BaseModel):
    """An explicitly untrusted candidate, regardless of extractor quality."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    extraction_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    extractor_id: str = Field(min_length=1)
    method: ExtractionMethod
    extracted_at: datetime
    scheme: Scheme

    @model_validator(mode="after")
    def require_draft(self) -> ExtractedSchemeCandidate:
        if self.extracted_at.tzinfo is None:
            raise ValueError("extracted_at must be timezone-aware")
        if self.scheme.publication_state is not PublicationState.DRAFT:
            raise ValueError("extracted candidates must remain draft")
        if any(source.document_id != self.document_id for source in self.scheme.official_sources):
            raise ValueError("candidate sources must belong to the extracted document")
        return self


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class ValidationIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    issue_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=1000)
    severity: ValidationSeverity
    source_ref_id: str | None = Field(default=None, min_length=1)


class ValidatedSchemeCandidate(BaseModel):
    """Locally schema-validated candidate; still not trusted or publishable directly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    extraction_id: str = Field(min_length=1)
    validator_version: str = Field(min_length=1)
    validated_at: datetime
    scheme: Scheme
    issues: tuple[ValidationIssue, ...] = ()

    @model_validator(mode="after")
    def require_draft(self) -> ValidatedSchemeCandidate:
        if self.validated_at.tzinfo is None:
            raise ValueError("validated_at must be timezone-aware")
        if self.scheme.publication_state is not PublicationState.DRAFT:
            raise ValueError("validated candidates must remain draft")
        issue_ids = [issue.issue_id for issue in self.issues]
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("validation issue IDs must be unique")
        return self


class HumanReviewApproval(BaseModel):
    """Human attestation plus the edited, source-approved scheme snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    review_id: str = Field(min_length=1)
    reviewer: TransitionActor
    reviewed_at: datetime
    reviewed_scheme: Scheme
    resolved_issue_ids: tuple[str, ...] = ()
    note: str | None = Field(default=None, min_length=1, max_length=2000)
    attested: Literal[True]

    @model_validator(mode="after")
    def require_human_approval(self) -> HumanReviewApproval:
        if self.reviewer.kind is not ActorKind.HUMAN:
            raise ValueError("review approval requires a human actor")
        if self.reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must be timezone-aware")
        if self.reviewed_scheme.publication_state is not PublicationState.IN_REVIEW:
            raise ValueError("reviewed scheme must remain in_review until publication")
        if any(
            source.review_status is not SourceReviewStatus.APPROVED
            for source in self.reviewed_scheme.official_sources
        ):
            raise ValueError("human-reviewed scheme sources must all be approved")
        if len(self.resolved_issue_ids) != len(set(self.resolved_issue_ids)):
            raise ValueError("resolved issue IDs must be unique")
        return self


class PublicationApproval(BaseModel):
    """A separate explicit authorization to expose a reviewed version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    publication_id: str = Field(min_length=1)
    publisher: TransitionActor
    published_at: datetime
    attested: Literal[True]

    @model_validator(mode="after")
    def require_human_publisher(self) -> PublicationApproval:
        if self.publisher.kind is not ActorKind.HUMAN:
            raise ValueError("publication requires a human actor")
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        return self


class IngestionRecord(BaseModel):
    """Immutable aggregate for one document ingestion attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ingestion_id: str = Field(min_length=1)
    source_document: SourceDocumentRecord
    state: IngestionState
    revision: int = Field(ge=0)
    parsed_document: ParsedDocument | None = None
    extracted_candidate: ExtractedSchemeCandidate | None = None
    validated_candidate: ValidatedSchemeCandidate | None = None
    human_review: HumanReviewApproval | None = None
    publication: PublishedSchemeVersion | None = None
    events: tuple[IngestionEvent, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> IngestionRecord:
        order = {
            IngestionState.RAW: 0,
            IngestionState.PARSED: 1,
            IngestionState.AUTO_EXTRACTED: 2,
            IngestionState.VALIDATED: 3,
            IngestionState.HUMAN_REVIEWED: 4,
            IngestionState.PUBLISHED: 5,
            IngestionState.RETIRED: 6,
        }
        required = (
            (1, self.parsed_document, "parsed_document"),
            (2, self.extracted_candidate, "extracted_candidate"),
            (3, self.validated_candidate, "validated_candidate"),
            (4, self.human_review, "human_review"),
            (5, self.publication, "publication"),
        )
        current = order[self.state]
        for threshold, value, field_name in required:
            if current >= threshold and value is None:
                raise ValueError(f"{self.state.value} ingestion requires {field_name}")
            if current < threshold and value is not None:
                raise ValueError(f"{field_name} cannot exist in {self.state.value} state")
        if self.parsed_document and (
            self.parsed_document.document_id != self.source_document.document_id
        ):
            raise ValueError("parsed document does not match source document")
        if self.extracted_candidate and self.validated_candidate:
            if self.validated_candidate.extraction_id != self.extracted_candidate.extraction_id:
                raise ValueError("validated candidate does not match extraction")
        if self.events[-1].to_state is not self.state:
            raise ValueError("last event must describe the current state")
        if self.events[-1].revision != self.revision:
            raise ValueError("last event revision must match the record revision")
        revisions = [event.revision for event in self.events]
        if revisions != list(range(len(self.events))):
            raise ValueError("event revisions must be contiguous from zero")
        return self
