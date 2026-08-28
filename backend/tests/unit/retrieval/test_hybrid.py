from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from kisanpath.domain.scheme import Scheme
from kisanpath.ingestion.lifecycle import IngestionLifecycle
from kisanpath.persistence.memory import InMemorySchemeStore
from kisanpath.persistence.models import PublishedDocumentChunk, PublishedSchemeVersion
from kisanpath.retrieval.hybrid import HybridRetrievalService
from kisanpath.retrieval.models import (
    HybridRetrievalResult,
    RetrievalFilters,
    RetrievalQuery,
    SemanticMatch,
    StructuredMatch,
)
from kisanpath.retrieval.structured import PublishedCorpusStructuredRetriever

FIXED_TIME = datetime(2026, 8, 28, 10, 0, tzinfo=UTC)


class FixedStructuredRetriever:
    def __init__(self, matches: tuple[StructuredMatch, ...]) -> None:
        self.matches = matches

    async def search(self, query: RetrievalQuery) -> tuple[StructuredMatch, ...]:
        return self.matches


class FixedSemanticRetriever:
    def __init__(self, matches: tuple[SemanticMatch, ...]) -> None:
        self.matches = matches

    async def search(self, query: RetrievalQuery) -> tuple[SemanticMatch, ...]:
        return self.matches


async def _published_fixture(
    fixture: Any,
) -> tuple[InMemorySchemeStore, PublishedSchemeVersion, tuple[PublishedDocumentChunk, ...]]:
    record = IngestionLifecycle.register(
        ingestion_id="retrieval-ingestion",
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
    record = IngestionLifecycle.record_human_review(record, fixture.review)
    published, publication, chunks = IngestionLifecycle.publish(record, fixture.publication)
    store = InMemorySchemeStore()
    await store.add_ingestion(record)
    await store.commit_publication(
        published, publication, chunks, expected_revision=record.revision
    )
    return store, publication, chunks


@pytest.mark.asyncio
async def test_hybrid_retrieval_deduplicates_and_returns_published_evidence(
    synthetic_pipeline: Any,
) -> None:
    store, publication, chunks = await _published_fixture(synthetic_pipeline)
    service = HybridRetrievalService(
        corpus=store,
        structured=FixedStructuredRetriever(
            (
                StructuredMatch(
                    publication=publication,
                    score=0.8,
                    signals=("jurisdiction_state",),
                    source_ref_ids=("synthetic-source-001",),
                ),
            )
        ),
        semantic=FixedSemanticRetriever(
            (
                SemanticMatch(
                    publication=publication,
                    score=0.9,
                    matched_chunk_ids=(chunks[2].chunk_id,),
                ),
            )
        ),
    )

    results = await service.search(RetrievalQuery(text="drip irrigation support"))

    assert len(results) == 1
    assert results[0].decision_scope == "discovery_only"
    assert results[0].fused_score == pytest.approx(0.83)
    assert {evidence.chunk_id for evidence in results[0].evidence} == {
        chunks[0].chunk_id,
        chunks[2].chunk_id,
    }
    assert "eligibility_status" not in HybridRetrievalResult.model_fields


@pytest.mark.asyncio
async def test_semantic_match_for_retired_version_is_excluded(
    synthetic_pipeline: Any,
) -> None:
    store, publication, chunks = await _published_fixture(synthetic_pipeline)
    await store.retire(publication.scheme_id, publication.version_id)
    service = HybridRetrievalService(
        corpus=store,
        structured=FixedStructuredRetriever(()),
        semantic=FixedSemanticRetriever(
            (
                SemanticMatch(
                    publication=publication,
                    score=1,
                    matched_chunk_ids=(chunks[0].chunk_id,),
                ),
            )
        ),
    )

    assert await service.search(RetrievalQuery(text="perfect semantic match")) == ()


@pytest.mark.asyncio
async def test_structured_retriever_uses_exact_published_filters(
    synthetic_pipeline: Any,
) -> None:
    store, publication, _ = await _published_fixture(synthetic_pipeline)
    retriever = PublishedCorpusStructuredRetriever(store)

    matches = await retriever.search(
        RetrievalQuery(
            text="irrigation",
            filters=RetrievalFilters(
                state="Gujarat",
                categories=("micro-irrigation",),
            ),
        )
    )
    rejected = await retriever.search(
        RetrievalQuery(text="irrigation", filters=RetrievalFilters(state="Rajasthan"))
    )

    assert matches[0].publication == publication
    assert set(matches[0].signals) == {"jurisdiction_state", "category"}
    assert rejected == ()


@pytest.mark.asyncio
async def test_active_corpus_rejects_lane_publication_identity_mismatch(
    synthetic_pipeline: Any,
) -> None:
    store, publication, chunks = await _published_fixture(synthetic_pipeline)
    payload = publication.model_dump(mode="python")
    payload["publication_id"] = "forged-publication-id"
    forged = PublishedSchemeVersion.model_validate(payload)
    service = HybridRetrievalService(
        corpus=store,
        structured=FixedStructuredRetriever(()),
        semantic=FixedSemanticRetriever(
            (
                SemanticMatch(
                    publication=forged,
                    score=1,
                    matched_chunk_ids=(chunks[0].chunk_id,),
                ),
            )
        ),
    )

    assert await service.search(RetrievalQuery(text="forged result")) == ()


@pytest.mark.asyncio
async def test_deterministic_match_ranks_before_higher_semantic_only_match(
    synthetic_pipeline: Any,
) -> None:
    store, structured_publication, chunks = await _published_fixture(synthetic_pipeline)
    scheme_payload = structured_publication.scheme.model_dump(mode="python")
    scheme_payload["scheme_id"] = "synthetic-scheme-semantic-only"
    scheme_payload["name"] = "Synthetic Semantic-only Scheme"
    scheme_payload["version"]["version_id"] = "synthetic-version-semantic-only"
    for rule in scheme_payload["eligibility_rules"]:
        rule["scheme_id"] = scheme_payload["scheme_id"]
    semantic_scheme = Scheme.model_validate(scheme_payload)
    semantic_publication = PublishedSchemeVersion(
        publication_id="synthetic-publication-semantic-only",
        scheme=semantic_scheme,
        human_review_id="synthetic-review-semantic-only",
        published_by="synthetic-publisher",
        published_at=structured_publication.published_at,
    )
    semantic_chunks = tuple(
        PublishedDocumentChunk(
            **{
                **chunk.model_dump(mode="python"),
                "chunk_id": f"semantic-{chunk.chunk_id}",
                "scheme_id": semantic_publication.scheme_id,
                "version_id": semantic_publication.version_id,
                "publication_id": semantic_publication.publication_id,
            }
        )
        for chunk in chunks
    )
    await store.publish(semantic_publication, semantic_chunks)
    service = HybridRetrievalService(
        corpus=store,
        structured=FixedStructuredRetriever(
            (
                StructuredMatch(
                    publication=structured_publication,
                    score=0.2,
                    signals=("jurisdiction_state",),
                ),
            )
        ),
        semantic=FixedSemanticRetriever(
            (
                SemanticMatch(
                    publication=semantic_publication,
                    score=1,
                    matched_chunk_ids=(semantic_chunks[0].chunk_id,),
                ),
            )
        ),
    )

    results = await service.search(RetrievalQuery(text="semantic preference check"))

    assert [result.publication.scheme_id for result in results] == [
        structured_publication.scheme_id,
        semantic_publication.scheme_id,
    ]
