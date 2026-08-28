"""Pure deterministic state transitions for scheme ingestion."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from kisanpath.domain.scheme import PublicationState, Scheme
from kisanpath.ingestion.exceptions import (
    InvalidIngestionTransitionError,
    PublicationGateError,
)
from kisanpath.ingestion.models import (
    ExtractedSchemeCandidate,
    HumanReviewApproval,
    IngestionEvent,
    IngestionRecord,
    IngestionState,
    ParsedDocument,
    PublicationApproval,
    TransitionActor,
    ValidatedSchemeCandidate,
    ValidationSeverity,
)
from kisanpath.persistence.models import (
    PublishedDocumentChunk,
    PublishedSchemeVersion,
    SourceDocumentRecord,
)


def _new_event_id() -> str:
    return f"ing-event-{uuid4()}"


class IngestionLifecycle:
    """Builds immutable records and refuses skipped trust transitions."""

    @staticmethod
    def register(
        *,
        ingestion_id: str,
        source_document: SourceDocumentRecord,
        actor: TransitionActor,
        occurred_at: datetime,
        event_id: str | None = None,
    ) -> IngestionRecord:
        event = IngestionEvent(
            event_id=event_id or _new_event_id(),
            from_state=None,
            to_state=IngestionState.RAW,
            actor=actor,
            occurred_at=occurred_at,
            revision=0,
        )
        return IngestionRecord(
            ingestion_id=ingestion_id,
            source_document=source_document,
            state=IngestionState.RAW,
            revision=0,
            events=(event,),
        )

    @classmethod
    def record_parsed(
        cls,
        record: IngestionRecord,
        parsed_document: ParsedDocument,
        *,
        actor: TransitionActor,
        occurred_at: datetime,
        event_id: str | None = None,
    ) -> IngestionRecord:
        if parsed_document.document_id != record.source_document.document_id:
            raise PublicationGateError("parsed document does not match ingestion source")
        return cls._transition(
            record,
            expected=IngestionState.RAW,
            target=IngestionState.PARSED,
            actor=actor,
            occurred_at=occurred_at,
            event_id=event_id,
            parsed_document=parsed_document,
        )

    @classmethod
    def record_extraction(
        cls,
        record: IngestionRecord,
        candidate: ExtractedSchemeCandidate,
        *,
        actor: TransitionActor,
        occurred_at: datetime,
        event_id: str | None = None,
    ) -> IngestionRecord:
        if candidate.document_id != record.source_document.document_id:
            raise PublicationGateError("extraction does not match ingestion source")
        return cls._transition(
            record,
            expected=IngestionState.PARSED,
            target=IngestionState.AUTO_EXTRACTED,
            actor=actor,
            occurred_at=occurred_at,
            event_id=event_id,
            extracted_candidate=candidate,
        )

    @classmethod
    def record_validation(
        cls,
        record: IngestionRecord,
        candidate: ValidatedSchemeCandidate,
        *,
        actor: TransitionActor,
        occurred_at: datetime,
        event_id: str | None = None,
    ) -> IngestionRecord:
        extracted = record.extracted_candidate
        if extracted is None or candidate.extraction_id != extracted.extraction_id:
            raise PublicationGateError("validation does not match recorded extraction")
        if candidate.scheme.scheme_id != extracted.scheme.scheme_id:
            raise PublicationGateError("validation cannot replace the extracted scheme identity")
        if candidate.scheme.version.version_id != extracted.scheme.version.version_id:
            raise PublicationGateError("validation cannot replace the extracted version identity")
        return cls._transition(
            record,
            expected=IngestionState.AUTO_EXTRACTED,
            target=IngestionState.VALIDATED,
            actor=actor,
            occurred_at=occurred_at,
            event_id=event_id,
            validated_candidate=candidate,
        )

    @classmethod
    def record_human_review(
        cls,
        record: IngestionRecord,
        approval: HumanReviewApproval,
        *,
        event_id: str | None = None,
    ) -> IngestionRecord:
        validated = record.validated_candidate
        if validated is None:
            raise PublicationGateError("human review requires a validated candidate")
        reviewed = approval.reviewed_scheme
        if reviewed.scheme_id != validated.scheme.scheme_id:
            raise PublicationGateError("review cannot replace the validated scheme identity")
        if reviewed.version.version_id != validated.scheme.version.version_id:
            raise PublicationGateError("review cannot replace the validated version identity")
        blocking_ids = {
            issue.issue_id
            for issue in validated.issues
            if issue.severity is ValidationSeverity.BLOCKING
        }
        unresolved = blocking_ids.difference(approval.resolved_issue_ids)
        if unresolved:
            raise PublicationGateError(
                f"blocking validation issues are unresolved: {sorted(unresolved)}"
            )
        return cls._transition(
            record,
            expected=IngestionState.VALIDATED,
            target=IngestionState.HUMAN_REVIEWED,
            actor=approval.reviewer,
            occurred_at=approval.reviewed_at,
            event_id=event_id,
            note=approval.note,
            human_review=approval,
        )

    @classmethod
    def publish(
        cls,
        record: IngestionRecord,
        approval: PublicationApproval,
        *,
        event_id: str | None = None,
    ) -> tuple[
        IngestionRecord,
        PublishedSchemeVersion,
        tuple[PublishedDocumentChunk, ...],
    ]:
        cls._expect(record, IngestionState.HUMAN_REVIEWED)
        review = record.human_review
        parsed = record.parsed_document
        if review is None or parsed is None:
            raise PublicationGateError("publication requires review and parsed provenance")

        reviewed_scheme = review.reviewed_scheme
        source_ids = {source.source_id for source in reviewed_scheme.official_sources}
        chunk_source_ids = {chunk.source_ref_id for chunk in parsed.chunks}
        missing_chunks = source_ids.difference(chunk_source_ids)
        if missing_chunks:
            raise PublicationGateError(
                f"approved sources have no parsed evidence chunk: {sorted(missing_chunks)}"
            )

        scheme_payload = reviewed_scheme.model_dump(mode="python")
        scheme_payload["publication_state"] = PublicationState.PUBLISHED
        published_scheme = Scheme.model_validate(scheme_payload)
        publication = PublishedSchemeVersion(
            publication_id=approval.publication_id,
            scheme=published_scheme,
            human_review_id=review.review_id,
            published_by=approval.publisher.actor_id,
            published_at=approval.published_at,
        )
        published_chunks = tuple(
            PublishedDocumentChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                source_ref_id=chunk.source_ref_id,
                scheme_id=published_scheme.scheme_id,
                version_id=published_scheme.version.version_id,
                publication_id=publication.publication_id,
                locator=chunk.locator,
                text=chunk.text,
                ordinal=chunk.ordinal,
                published_at=approval.published_at,
            )
            for chunk in parsed.chunks
            if chunk.source_ref_id in source_ids
        )
        updated = cls._transition(
            record,
            expected=IngestionState.HUMAN_REVIEWED,
            target=IngestionState.PUBLISHED,
            actor=approval.publisher,
            occurred_at=approval.published_at,
            event_id=event_id,
            publication=publication,
        )
        return updated, publication, published_chunks

    @classmethod
    def retire(
        cls,
        record: IngestionRecord,
        *,
        actor: TransitionActor,
        occurred_at: datetime,
        reason: str,
        event_id: str | None = None,
    ) -> IngestionRecord:
        return cls._transition(
            record,
            expected=IngestionState.PUBLISHED,
            target=IngestionState.RETIRED,
            actor=actor,
            occurred_at=occurred_at,
            event_id=event_id,
            note=reason,
        )

    @staticmethod
    def _expect(record: IngestionRecord, expected: IngestionState) -> None:
        if record.state is not expected:
            raise InvalidIngestionTransitionError(
                f"expected {expected.value}, found {record.state.value}"
            )

    @classmethod
    def _transition(
        cls,
        record: IngestionRecord,
        *,
        expected: IngestionState,
        target: IngestionState,
        actor: TransitionActor,
        occurred_at: datetime,
        event_id: str | None,
        note: str | None = None,
        **updates: object,
    ) -> IngestionRecord:
        cls._expect(record, expected)
        revision = record.revision + 1
        event = IngestionEvent(
            event_id=event_id or _new_event_id(),
            from_state=record.state,
            to_state=target,
            actor=actor,
            occurred_at=occurred_at,
            revision=revision,
            note=note,
        )
        payload = record.model_dump(mode="python")
        payload.update(updates)
        payload.update(
            state=target,
            revision=revision,
            events=(*record.events, event),
        )
        return IngestionRecord.model_validate(payload)
