"""Basic deterministic filtering over the published corpus."""

from __future__ import annotations

from kisanpath.persistence.repositories import PublishedCorpusRepository
from kisanpath.retrieval.models import RetrievalQuery, StructuredMatch


class PublishedCorpusStructuredRetriever:
    """Exact canonical filters; normalization belongs upstream."""

    def __init__(self, corpus: PublishedCorpusRepository) -> None:
        self._corpus = corpus

    async def search(self, query: RetrievalQuery) -> tuple[StructuredMatch, ...]:
        matches: list[StructuredMatch] = []
        for publication in await self._corpus.list_active():
            scheme = publication.scheme
            signals: list[str] = []
            filters = query.filters
            if filters.state:
                state_matches = scheme.jurisdiction.nationwide or any(
                    state.casefold() == filters.state.casefold()
                    for state in scheme.jurisdiction.states
                )
                if not state_matches:
                    continue
                signals.append("jurisdiction_state")
            if filters.district:
                district_matches = not scheme.jurisdiction.districts or any(
                    district.casefold() == filters.district.casefold()
                    for district in scheme.jurisdiction.districts
                )
                if not district_matches:
                    continue
                signals.append("jurisdiction_district")
            if filters.categories:
                scheme_categories = {category.casefold() for category in scheme.categories}
                requested = {category.casefold() for category in filters.categories}
                if not requested.intersection(scheme_categories):
                    continue
                signals.append("category")
            if filters.crops:
                # Crop applicability is not yet canonical scheme data; do not guess it.
                continue
            if not signals:
                signals.append("published_corpus")
            score = min(1.0, 0.4 + 0.2 * len(signals))
            matches.append(
                StructuredMatch(
                    publication=publication,
                    score=score,
                    signals=tuple(signals),
                )
            )
        return tuple(matches)
