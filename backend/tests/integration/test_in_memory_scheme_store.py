from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from kisanpath.ingestion.lifecycle import IngestionLifecycle
from kisanpath.persistence.exceptions import ConcurrentWriteError
from kisanpath.persistence.memory import InMemorySchemeStore

FIXED_TIME = datetime(2026, 8, 28, 10, 0, tzinfo=UTC)


def _reviewed_record(fixture: Any) -> Any:
    record = IngestionLifecycle.register(
        ingestion_id="ingestion-store-test",
        source_document=fixture.source,
        actor=fixture.system_actor,
        occurred_at=FIXED_TIME,
    )
    record = IngestionLifecycle.record_parsed(
        record,
        fixture.parsed,
        actor=fixture.system_actor,
        occurred_at=FIXED_TIME + timedelta(minutes=1),
    )
    record = IngestionLifecycle.record_extraction(
        record,
        fixture.extracted,
        actor=fixture.system_actor,
        occurred_at=FIXED_TIME + timedelta(minutes=2),
    )
    record = IngestionLifecycle.record_validation(
        record,
        fixture.validated,
        actor=fixture.system_actor,
        occurred_at=FIXED_TIME + timedelta(minutes=3),
    )
    return IngestionLifecycle.record_human_review(record, fixture.review)


@pytest.mark.asyncio
async def test_publication_unit_of_work_controls_corpus_visibility(
    synthetic_pipeline: Any,
) -> None:
    store = InMemorySchemeStore()
    reviewed = _reviewed_record(synthetic_pipeline)
    await store.add_source(synthetic_pipeline.source)
    await store.add_ingestion(reviewed)

    assert await store.list_active() == ()
    published, publication, chunks = IngestionLifecycle.publish(
        reviewed, synthetic_pipeline.publication
    )
    await store.commit_publication(
        published,
        publication,
        chunks,
        expected_revision=reviewed.revision,
    )

    assert await store.get_active(publication.scheme_id) == publication
    assert await store.list_chunks(publication.scheme_id, publication.version_id) == chunks
    assert await store.get_ingestion(reviewed.ingestion_id) == published


@pytest.mark.asyncio
async def test_optimistic_concurrency_rejects_stale_transition(
    synthetic_pipeline: Any,
) -> None:
    store = InMemorySchemeStore()
    reviewed = _reviewed_record(synthetic_pipeline)
    await store.add_ingestion(reviewed)
    published, publication, chunks = IngestionLifecycle.publish(
        reviewed, synthetic_pipeline.publication
    )

    with pytest.raises(ConcurrentWriteError, match="stale ingestion revision"):
        await store.commit_publication(
            published,
            publication,
            chunks,
            expected_revision=reviewed.revision - 1,
        )
    assert await store.list_active() == ()


@pytest.mark.asyncio
async def test_retired_version_is_removed_from_active_corpus(
    synthetic_pipeline: Any,
) -> None:
    store = InMemorySchemeStore()
    reviewed = _reviewed_record(synthetic_pipeline)
    await store.add_ingestion(reviewed)
    published, publication, chunks = IngestionLifecycle.publish(
        reviewed, synthetic_pipeline.publication
    )
    await store.commit_publication(
        published, publication, chunks, expected_revision=reviewed.revision
    )
    retired = IngestionLifecycle.retire(
        published,
        actor=synthetic_pipeline.publication.publisher,
        occurred_at=FIXED_TIME + timedelta(minutes=6),
        reason="Synthetic retirement test.",
    )
    await store.commit_retirement(
        retired,
        expected_revision=published.revision,
    )

    assert await store.get_active(publication.scheme_id) is None
    assert await store.list_chunks(publication.scheme_id, publication.version_id) == ()
    assert await store.get_version(publication.scheme_id, publication.version_id) == publication
