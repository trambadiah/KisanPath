"""Async repository ports; concrete databases remain replaceable."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from kisanpath.persistence.models import (
    PublishedDocumentChunk,
    PublishedSchemeVersion,
    SourceDocumentRecord,
)

if TYPE_CHECKING:
    from kisanpath.ingestion.models import IngestionRecord


class SourceDocumentRepository(Protocol):
    async def add_source(self, document: SourceDocumentRecord) -> None: ...

    async def get_source(self, document_id: str) -> SourceDocumentRecord | None: ...


class IngestionRepository(Protocol):
    """Stores the untrusted lifecycle aggregate with optimistic concurrency."""

    async def add_ingestion(self, record: IngestionRecord) -> None: ...

    async def get_ingestion(self, ingestion_id: str) -> IngestionRecord | None: ...

    async def save(self, record: IngestionRecord, *, expected_revision: int) -> None: ...


class PublishedCorpusRepository(Protocol):
    """Atomic write/read boundary for eligibility-visible content."""

    async def publish(
        self,
        record: PublishedSchemeVersion,
        chunks: tuple[PublishedDocumentChunk, ...],
    ) -> None: ...

    async def retire(self, scheme_id: str, version_id: str) -> None: ...

    async def get_active(self, scheme_id: str) -> PublishedSchemeVersion | None: ...

    async def get_version(
        self, scheme_id: str, version_id: str
    ) -> PublishedSchemeVersion | None: ...

    async def list_active(self) -> tuple[PublishedSchemeVersion, ...]: ...

    async def list_chunks(
        self, scheme_id: str, version_id: str
    ) -> tuple[PublishedDocumentChunk, ...]: ...


class PublicationUnitOfWork(Protocol):
    """Transaction boundary coupling lifecycle state with corpus visibility."""

    async def commit_publication(
        self,
        ingestion: IngestionRecord,
        publication: PublishedSchemeVersion,
        chunks: tuple[PublishedDocumentChunk, ...],
        *,
        expected_revision: int,
    ) -> None: ...

    async def commit_retirement(
        self,
        ingestion: IngestionRecord,
        *,
        expected_revision: int,
    ) -> None: ...
