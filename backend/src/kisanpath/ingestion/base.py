"""Provider-neutral ports for parsing, extraction, and local validation."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from kisanpath.ingestion.models import (
    ExtractedSchemeCandidate,
    ParsedDocument,
    ValidatedSchemeCandidate,
)
from kisanpath.persistence.models import SourceDocumentRecord


class RawDocumentContent(BaseModel):
    """Content supplied by an acquisition adapter, separate from provenance metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class DocumentParser(Protocol):
    async def parse(
        self, document: SourceDocumentRecord, content: RawDocumentContent
    ) -> ParsedDocument: ...


class SchemeCandidateExtractor(Protocol):
    """Extraction can use an LLM internally but returns an untrusted typed candidate."""

    async def extract(
        self, document: SourceDocumentRecord, parsed: ParsedDocument
    ) -> ExtractedSchemeCandidate: ...


class SchemeCandidateValidator(Protocol):
    """Local deterministic/schema validation boundary."""

    def validate(self, candidate: ExtractedSchemeCandidate) -> ValidatedSchemeCandidate: ...
