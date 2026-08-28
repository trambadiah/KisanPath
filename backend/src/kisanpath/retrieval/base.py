"""Interfaces for independently replaceable structured and semantic retrieval."""

from __future__ import annotations

from typing import Protocol

from kisanpath.retrieval.models import RetrievalQuery, SemanticMatch, StructuredMatch


class StructuredSchemeRetriever(Protocol):
    async def search(self, query: RetrievalQuery) -> tuple[StructuredMatch, ...]: ...


class SemanticSchemeRetriever(Protocol):
    async def search(self, query: RetrievalQuery) -> tuple[SemanticMatch, ...]: ...
