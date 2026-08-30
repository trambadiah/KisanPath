"""Deterministic fusion over independent structured and semantic lanes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import perf_counter

from kisanpath.observability.metrics import MetricsSink, NoopMetrics
from kisanpath.observability.tracing import NoopTracer, Tracer
from kisanpath.persistence.models import PublishedDocumentChunk, PublishedSchemeVersion
from kisanpath.persistence.repositories import PublishedCorpusRepository
from kisanpath.retrieval.base import SemanticSchemeRetriever, StructuredSchemeRetriever
from kisanpath.retrieval.models import (
    HybridRetrievalResult,
    RetrievalEvidence,
    RetrievalQuery,
    SemanticMatch,
    StructuredMatch,
)
from kisanpath.security.evidence import prepare_untrusted_evidence


@dataclass
class _Candidate:
    publication: PublishedSchemeVersion
    structured_score: float | None = None
    semantic_score: float | None = None
    signals: set[str] = field(default_factory=set)
    source_ref_ids: set[str] = field(default_factory=set)
    chunk_ids: set[str] = field(default_factory=set)


class HybridRetrievalService:
    """Fuses discovery signals after checking them against the active corpus."""

    def __init__(
        self,
        *,
        corpus: PublishedCorpusRepository,
        structured: StructuredSchemeRetriever,
        semantic: SemanticSchemeRetriever,
        structured_weight: float = 0.7,
        metrics: MetricsSink | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        if not 0 <= structured_weight <= 1:
            raise ValueError("structured_weight must be between zero and one")
        self._corpus = corpus
        self._structured = structured
        self._semantic = semantic
        self._structured_weight = structured_weight
        self._metrics = metrics or NoopMetrics()
        self._tracer = tracer or NoopTracer()

    async def search(self, query: RetrievalQuery) -> tuple[HybridRetrievalResult, ...]:
        started = perf_counter()
        async with self._tracer.start_span(
            "retrieval.hybrid",
            attributes={"top_k": query.top_k, "language": query.language},
        ) as span:
            results = await self._search(query)
            span.set_attribute("candidates_returned", len(results))
        self._metrics.observe(
            "kisanpath_retrieval_duration_ms",
            (perf_counter() - started) * 1000,
        )
        self._metrics.observe(
            "kisanpath_retrieval_candidates",
            len(results),
        )
        return results

    async def _search(self, query: RetrievalQuery) -> tuple[HybridRetrievalResult, ...]:
        structured_matches, semantic_matches, active = await asyncio.gather(
            self._structured.search(query),
            self._semantic.search(query),
            self._corpus.list_active(),
        )
        active_by_key = {
            (publication.scheme_id, publication.version_id): publication for publication in active
        }
        candidates: dict[tuple[str, str], _Candidate] = {}
        for structured_match in structured_matches:
            self._merge_structured(candidates, active_by_key, structured_match)
        for semantic_match in semantic_matches:
            self._merge_semantic(candidates, active_by_key, semantic_match)

        results = await asyncio.gather(
            *(self._build_result(candidate) for candidate in candidates.values())
        )
        ranked = sorted(
            (result for result in results if result is not None),
            key=lambda result: (
                result.structured_score is None,
                -(result.structured_score or 0),
                -(result.semantic_score or 0),
                result.publication.scheme_id,
                result.publication.version_id,
            ),
        )
        return tuple(ranked[: query.top_k])

    @staticmethod
    def _merge_structured(
        candidates: dict[tuple[str, str], _Candidate],
        active: dict[tuple[str, str], PublishedSchemeVersion],
        match: StructuredMatch,
    ) -> None:
        key = (match.publication.scheme_id, match.publication.version_id)
        publication = active.get(key)
        if publication is None or publication.publication_id != match.publication.publication_id:
            return
        candidate = candidates.setdefault(key, _Candidate(publication=publication))
        candidate.structured_score = max(candidate.structured_score or 0, match.score)
        candidate.signals.update(match.signals)
        candidate.source_ref_ids.update(match.source_ref_ids)

    @staticmethod
    def _merge_semantic(
        candidates: dict[tuple[str, str], _Candidate],
        active: dict[tuple[str, str], PublishedSchemeVersion],
        match: SemanticMatch,
    ) -> None:
        key = (match.publication.scheme_id, match.publication.version_id)
        publication = active.get(key)
        if publication is None or publication.publication_id != match.publication.publication_id:
            return
        candidate = candidates.setdefault(key, _Candidate(publication=publication))
        candidate.semantic_score = max(candidate.semantic_score or 0, match.score)
        candidate.chunk_ids.update(match.matched_chunk_ids)

    async def _build_result(self, candidate: _Candidate) -> HybridRetrievalResult | None:
        chunks = await self._corpus.list_chunks(
            candidate.publication.scheme_id,
            candidate.publication.version_id,
        )
        evidence_chunks = self._select_evidence(chunks, candidate)
        if not evidence_chunks:
            return None
        structured_score = candidate.structured_score
        semantic_score = candidate.semantic_score
        fused_score = self._structured_weight * (structured_score or 0) + (
            1 - self._structured_weight
        ) * (semantic_score or 0)
        evidence_items: list[RetrievalEvidence] = []
        for chunk in evidence_chunks:
            prepared = prepare_untrusted_evidence(
                chunk.text,
                source_ref_id=chunk.source_ref_id,
                locator=chunk.locator,
            )
            evidence_items.append(
                RetrievalEvidence(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    source_ref_id=chunk.source_ref_id,
                    locator=chunk.locator,
                    bounded_excerpt=prepared.text,
                    security_flags=prepared.suspicious_markers,
                )
            )
        evidence = tuple(evidence_items)
        return HybridRetrievalResult(
            publication=candidate.publication,
            structured_score=structured_score,
            semantic_score=semantic_score,
            fused_score=fused_score,
            structured_signals=tuple(sorted(candidate.signals)),
            evidence=evidence,
        )

    @staticmethod
    def _select_evidence(
        chunks: tuple[PublishedDocumentChunk, ...], candidate: _Candidate
    ) -> tuple[PublishedDocumentChunk, ...]:
        selected = tuple(
            chunk
            for chunk in chunks
            if chunk.chunk_id in candidate.chunk_ids
            or chunk.source_ref_id in candidate.source_ref_ids
        )
        if selected:
            return selected
        return chunks[:1]
