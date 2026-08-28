"""Deterministic in-memory adapters for tests and local examples."""

from __future__ import annotations

from kisanpath.ingestion.models import IngestionRecord, IngestionState
from kisanpath.persistence.exceptions import (
    ConcurrentWriteError,
    RecordAlreadyExistsError,
)
from kisanpath.persistence.models import (
    PublishedDocumentChunk,
    PublishedSchemeVersion,
    SourceDocumentRecord,
)


class InMemorySchemeStore:
    """Implements all persistence ports and atomic publication for tests."""

    def __init__(self) -> None:
        self._sources: dict[str, SourceDocumentRecord] = {}
        self._ingestions: dict[str, IngestionRecord] = {}
        self._publications: dict[tuple[str, str], PublishedSchemeVersion] = {}
        self._chunks: dict[tuple[str, str], tuple[PublishedDocumentChunk, ...]] = {}
        self._retired: set[tuple[str, str]] = set()

    async def add_source(self, document: SourceDocumentRecord) -> None:
        if document.document_id in self._sources:
            raise RecordAlreadyExistsError(
                f"source document already exists: {document.document_id}"
            )
        self._sources[document.document_id] = document

    async def add_ingestion(self, record: IngestionRecord) -> None:
        if record.ingestion_id in self._ingestions:
            raise RecordAlreadyExistsError(f"ingestion already exists: {record.ingestion_id}")
        self._ingestions[record.ingestion_id] = record

    async def get_source(self, document_id: str) -> SourceDocumentRecord | None:
        return self._sources.get(document_id)

    async def get_ingestion(self, ingestion_id: str) -> IngestionRecord | None:
        return self._ingestions.get(ingestion_id)

    async def save(self, record: IngestionRecord, *, expected_revision: int) -> None:
        current = self._ingestions.get(record.ingestion_id)
        self._verify_revision(current, expected_revision, record.ingestion_id)
        self._ingestions[record.ingestion_id] = record

    async def publish(
        self,
        record: PublishedSchemeVersion,
        chunks: tuple[PublishedDocumentChunk, ...],
    ) -> None:
        key = (record.scheme_id, record.version_id)
        self._verify_publication(record, chunks)
        if key in self._publications:
            raise RecordAlreadyExistsError(
                f"scheme version already published: {record.scheme_id}/{record.version_id}"
            )
        if await self.get_active(record.scheme_id) is not None:
            raise RecordAlreadyExistsError(
                f"scheme already has an active version: {record.scheme_id}"
            )
        self._publications[key] = record
        self._chunks[key] = chunks

    async def retire(self, scheme_id: str, version_id: str) -> None:
        key = (scheme_id, version_id)
        if key not in self._publications:
            raise RecordAlreadyExistsError(
                f"cannot retire unpublished scheme version: {scheme_id}/{version_id}"
            )
        self._retired.add(key)

    async def get_active(self, scheme_id: str) -> PublishedSchemeVersion | None:
        active = [
            publication
            for key, publication in self._publications.items()
            if key[0] == scheme_id and key not in self._retired
        ]
        if not active:
            return None
        return sorted(active, key=lambda item: item.published_at)[-1]

    async def get_version(self, scheme_id: str, version_id: str) -> PublishedSchemeVersion | None:
        return self._publications.get((scheme_id, version_id))

    async def list_active(self) -> tuple[PublishedSchemeVersion, ...]:
        return tuple(
            sorted(
                (
                    publication
                    for key, publication in self._publications.items()
                    if key not in self._retired
                ),
                key=lambda item: (item.scheme_id, item.version_id),
            )
        )

    async def list_chunks(
        self, scheme_id: str, version_id: str
    ) -> tuple[PublishedDocumentChunk, ...]:
        key = (scheme_id, version_id)
        if key in self._retired:
            return ()
        return self._chunks.get(key, ())

    async def commit_publication(
        self,
        ingestion: IngestionRecord,
        publication: PublishedSchemeVersion,
        chunks: tuple[PublishedDocumentChunk, ...],
        *,
        expected_revision: int,
    ) -> None:
        if ingestion.state is not IngestionState.PUBLISHED:
            raise ValueError("publication commit requires a published ingestion")
        if ingestion.publication != publication:
            raise ValueError("ingestion publication does not match corpus projection")
        current = self._ingestions.get(ingestion.ingestion_id)
        self._verify_revision(current, expected_revision, ingestion.ingestion_id)
        await self.publish(publication, chunks)
        self._ingestions[ingestion.ingestion_id] = ingestion

    async def commit_retirement(
        self,
        ingestion: IngestionRecord,
        *,
        expected_revision: int,
    ) -> None:
        if ingestion.state is not IngestionState.RETIRED or ingestion.publication is None:
            raise ValueError("retirement commit requires a retired published ingestion")
        current = self._ingestions.get(ingestion.ingestion_id)
        self._verify_revision(current, expected_revision, ingestion.ingestion_id)
        await self.retire(
            ingestion.publication.scheme_id,
            ingestion.publication.version_id,
        )
        self._ingestions[ingestion.ingestion_id] = ingestion

    @staticmethod
    def _verify_revision(
        current: IngestionRecord | None, expected_revision: int, record_id: str
    ) -> None:
        if current is None:
            raise ConcurrentWriteError(f"ingestion does not exist: {record_id}")
        if current.revision != expected_revision:
            raise ConcurrentWriteError(
                f"stale ingestion revision for {record_id}: "
                f"expected {expected_revision}, found {current.revision}"
            )

    @staticmethod
    def _verify_publication(
        record: PublishedSchemeVersion,
        chunks: tuple[PublishedDocumentChunk, ...],
    ) -> None:
        if not chunks:
            raise ValueError("a published scheme requires evidence chunks")
        for chunk in chunks:
            if (
                chunk.scheme_id != record.scheme_id
                or chunk.version_id != record.version_id
                or chunk.publication_id != record.publication_id
            ):
                raise ValueError("published chunk does not match scheme publication")
