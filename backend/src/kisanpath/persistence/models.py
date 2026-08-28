"""Storage-neutral records for source material and the trusted corpus."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kisanpath.domain.scheme import PublicationState, Scheme


class SourceDocumentRecord(BaseModel):
    """Immutable provenance metadata for an acquired document snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    origin_locator: str = Field(min_length=1)
    snapshot_locator: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    imported_at: datetime
    imported_by: str = Field(min_length=1)
    synthetic: bool = False

    @model_validator(mode="after")
    def require_aware_timestamp(self) -> SourceDocumentRecord:
        if self.imported_at.tzinfo is None:
            raise ValueError("imported_at must be timezone-aware")
        return self


class ParsedDocumentChunk(BaseModel):
    """An untrusted parsed chunk with a stable provenance location."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_ref_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=8000)
    ordinal: int = Field(ge=0)


class PublishedSchemeVersion(BaseModel):
    """Eligibility-visible projection created only by the publication gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    publication_id: str = Field(min_length=1)
    scheme: Scheme
    human_review_id: str = Field(min_length=1)
    published_by: str = Field(min_length=1)
    published_at: datetime

    @model_validator(mode="after")
    def require_published_scheme(self) -> PublishedSchemeVersion:
        if self.scheme.publication_state is not PublicationState.PUBLISHED:
            raise ValueError("published corpus records require a published scheme")
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        return self

    @property
    def scheme_id(self) -> str:
        return self.scheme.scheme_id

    @property
    def version_id(self) -> str:
        return self.scheme.version.version_id


class PublishedDocumentChunk(BaseModel):
    """A source chunk explicitly promoted with a reviewed scheme version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_ref_id: str = Field(min_length=1)
    scheme_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=8000)
    ordinal: int = Field(ge=0)
    published_at: datetime

    @model_validator(mode="after")
    def require_aware_timestamp(self) -> PublishedDocumentChunk:
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        return self
