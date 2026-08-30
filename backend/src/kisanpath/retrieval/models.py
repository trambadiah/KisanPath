"""Storage- and vector-provider-neutral hybrid retrieval models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kisanpath.persistence.models import PublishedSchemeVersion


class RetrievalFilters(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: str | None = Field(default=None, min_length=1)
    district: str | None = Field(default=None, min_length=1)
    categories: tuple[str, ...] = ()
    crops: tuple[str, ...] = ()

    @model_validator(mode="after")
    def unique_filters(self) -> RetrievalFilters:
        for name in ("categories", "crops"):
            values = getattr(self, name)
            normalized = [value.casefold() for value in values]
            if len(normalized) != len(set(normalized)):
                raise ValueError(f"{name} filters must be unique")
        return self


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", min_length=2, max_length=20)
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)
    top_k: int = Field(default=10, ge=1, le=100)


class StructuredMatch(BaseModel):
    """Deterministic discovery match; it is not an eligibility decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    publication: PublishedSchemeVersion
    score: float = Field(ge=0, le=1)
    signals: tuple[str, ...] = Field(min_length=1)
    source_ref_ids: tuple[str, ...] = ()


class SemanticMatch(BaseModel):
    """Semantic relevance returned by an arbitrary vector/search backend."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    publication: PublishedSchemeVersion
    score: float = Field(ge=0, le=1)
    matched_chunk_ids: tuple[str, ...] = Field(min_length=1)


class RetrievalEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_ref_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    bounded_excerpt: str = Field(min_length=1, max_length=1000)
    security_flags: tuple[str, ...] = ()


class HybridRetrievalResult(BaseModel):
    """Ranked discovery result whose scores must never be read as eligibility."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    publication: PublishedSchemeVersion
    structured_score: float | None = Field(default=None, ge=0, le=1)
    semantic_score: float | None = Field(default=None, ge=0, le=1)
    fused_score: float = Field(ge=0, le=1)
    structured_signals: tuple[str, ...] = ()
    evidence: tuple[RetrievalEvidence, ...] = Field(min_length=1)
    decision_scope: Literal["discovery_only"] = "discovery_only"
