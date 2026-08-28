from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from kisanpath.domain.scheme import PublicationState
from kisanpath.ingestion.exceptions import (
    InvalidIngestionTransitionError,
    PublicationGateError,
)
from kisanpath.ingestion.lifecycle import IngestionLifecycle
from kisanpath.ingestion.models import (
    ActorKind,
    HumanReviewApproval,
    IngestionState,
    TransitionActor,
    ValidatedSchemeCandidate,
    ValidationIssue,
    ValidationSeverity,
)
from kisanpath.persistence.models import PublishedSchemeVersion

FIXED_TIME = datetime(2026, 8, 28, 10, 0, tzinfo=UTC)


def _to_validated(fixture: Any) -> Any:
    record = IngestionLifecycle.register(
        ingestion_id="synthetic-ingestion-001",
        source_document=fixture.source,
        actor=fixture.system_actor,
        occurred_at=FIXED_TIME,
        event_id="event-raw",
    )
    record = IngestionLifecycle.record_parsed(
        record,
        fixture.parsed,
        actor=fixture.system_actor,
        occurred_at=FIXED_TIME + timedelta(minutes=1),
        event_id="event-parsed",
    )
    record = IngestionLifecycle.record_extraction(
        record,
        fixture.extracted,
        actor=fixture.system_actor,
        occurred_at=FIXED_TIME + timedelta(minutes=2),
        event_id="event-extracted",
    )
    return IngestionLifecycle.record_validation(
        record,
        fixture.validated,
        actor=fixture.system_actor,
        occurred_at=FIXED_TIME + timedelta(minutes=3),
        event_id="event-validated",
    )


def test_full_lifecycle_creates_audited_immutable_publication(
    synthetic_pipeline: Any,
) -> None:
    validated = _to_validated(synthetic_pipeline)
    reviewed = IngestionLifecycle.record_human_review(
        validated,
        synthetic_pipeline.review,
        event_id="event-reviewed",
    )
    published, publication, chunks = IngestionLifecycle.publish(
        reviewed,
        synthetic_pipeline.publication,
        event_id="event-published",
    )

    assert published.state is IngestionState.PUBLISHED
    assert published.revision == 5
    assert tuple(event.to_state for event in published.events) == tuple(IngestionState)[:-1]
    assert publication.scheme.publication_state is PublicationState.PUBLISHED
    assert publication.human_review_id == synthetic_pipeline.review.review_id
    assert {chunk.source_ref_id for chunk in chunks} == {
        source.source_id for source in publication.scheme.official_sources
    }
    assert synthetic_pipeline.extracted.scheme.publication_state is PublicationState.DRAFT


def test_llm_extraction_cannot_skip_human_review(
    synthetic_pipeline: Any,
) -> None:
    validated = _to_validated(synthetic_pipeline)

    with pytest.raises(InvalidIngestionTransitionError, match="expected human_reviewed"):
        IngestionLifecycle.publish(validated, synthetic_pipeline.publication)


def test_extracted_draft_cannot_be_stored_as_published_version(
    synthetic_pipeline: Any,
) -> None:
    with pytest.raises(ValidationError, match="published corpus records require"):
        PublishedSchemeVersion(
            publication_id="invalid-publication",
            scheme=synthetic_pipeline.extracted.scheme,
            human_review_id="missing-review",
            published_by="automated-extractor",
            published_at=FIXED_TIME,
        )


def test_review_approval_rejects_system_actor(
    synthetic_pipeline: Any,
) -> None:
    with pytest.raises(ValidationError, match="human actor"):
        HumanReviewApproval(
            review_id="invalid-review",
            reviewer=TransitionActor(actor_id="extractor", kind=ActorKind.SYSTEM),
            reviewed_at=FIXED_TIME,
            reviewed_scheme=synthetic_pipeline.review.reviewed_scheme,
            attested=True,
        )


def test_blocking_validation_issue_requires_explicit_resolution(
    synthetic_pipeline: Any,
) -> None:
    issue = ValidationIssue(
        issue_id="ambiguous-threshold",
        code="ambiguous_rule",
        message="Threshold unit requires human confirmation.",
        severity=ValidationSeverity.BLOCKING,
        source_ref_id="synthetic-source-002",
    )
    validated_candidate = ValidatedSchemeCandidate(
        extraction_id=synthetic_pipeline.validated.extraction_id,
        validator_version="local-schema-v1",
        validated_at=synthetic_pipeline.validated.validated_at,
        scheme=synthetic_pipeline.validated.scheme,
        issues=(issue,),
    )
    fixture = type(synthetic_pipeline)(
        source=synthetic_pipeline.source,
        parsed=synthetic_pipeline.parsed,
        extracted=synthetic_pipeline.extracted,
        validated=validated_candidate,
        review=synthetic_pipeline.review,
        publication=synthetic_pipeline.publication,
        system_actor=synthetic_pipeline.system_actor,
    )
    validated = _to_validated(fixture)

    with pytest.raises(PublicationGateError, match="unresolved"):
        IngestionLifecycle.record_human_review(validated, fixture.review)


def test_retirement_preserves_history_and_records_reason(
    synthetic_pipeline: Any,
) -> None:
    validated = _to_validated(synthetic_pipeline)
    reviewed = IngestionLifecycle.record_human_review(validated, synthetic_pipeline.review)
    published, _, _ = IngestionLifecycle.publish(reviewed, synthetic_pipeline.publication)
    retired = IngestionLifecycle.retire(
        published,
        actor=synthetic_pipeline.publication.publisher,
        occurred_at=FIXED_TIME + timedelta(minutes=6),
        reason="Superseded by a later reviewed synthetic version.",
        event_id="event-retired",
    )

    assert retired.state is IngestionState.RETIRED
    assert retired.publication == published.publication
    assert retired.events[-1].note == "Superseded by a later reviewed synthetic version."
