"""Canonical reviewed scheme, source, version, and rule models."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator
from pydantic.types import JsonValue

from kisanpath.domain.eligibility import EligibilityOperator, RuleType


class SourceReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PublicationState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    RETIRED = "retired"


class SourceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    canonical_url: AnyHttpUrl | None = None
    source_locator: str | None = Field(default=None, min_length=1)
    title: str = Field(min_length=1)
    locator: str = Field(min_length=1, description="Page, section, or stable chunk locator")
    imported_at: datetime
    review_status: SourceReviewStatus
    bounded_excerpt: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def require_location(self) -> SourceReference:
        if self.canonical_url is None and self.source_locator is None:
            raise ValueError("a source requires canonical_url or source_locator")
        if self.imported_at.tzinfo is None:
            raise ValueError("imported_at must be timezone-aware")
        return self


class SourcedText(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1)
    source_ref_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_sources(self) -> SourcedText:
        if len(self.source_ref_ids) != len(set(self.source_ref_ids)):
            raise ValueError("source reference IDs must be unique")
        return self


class SchemeVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version_id: str = Field(min_length=1)
    effective_from: date
    effective_to: date | None = None
    corpus_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_window(self) -> SchemeVersion:
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        return self


class Jurisdiction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    country_code: str = Field(default="IN", pattern=r"^[A-Z]{2}$")
    nationwide: bool = False
    states: tuple[str, ...] = ()
    districts: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_scope(self) -> Jurisdiction:
        if self.nationwide and (self.states or self.districts):
            raise ValueError("nationwide jurisdiction cannot also list regions")
        if not self.nationwide and not self.states:
            raise ValueError("non-nationwide jurisdiction requires at least one state")
        if self.districts and len(self.states) != 1:
            raise ValueError("district restrictions require exactly one state")
        return self


_UNARY_OPERATORS = {
    EligibilityOperator.BOOLEAN_TRUE,
    EligibilityOperator.BOOLEAN_FALSE,
    EligibilityOperator.EXISTS,
    EligibilityOperator.NOT_EXISTS,
}


class EligibilityRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str = Field(min_length=1)
    scheme_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rule_type: RuleType
    field: str | None = Field(default=None, min_length=1)
    operator: EligibilityOperator | None = None
    expected_value: JsonValue = None
    normalization_rule: str | None = Field(default=None, min_length=1)
    required: bool = True
    source_ref_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_rule_shape(self) -> EligibilityRule:
        if self.rule_type is RuleType.DETERMINISTIC and (not self.field or not self.operator):
            raise ValueError("deterministic rules require field and operator")
        if self.operator in _UNARY_OPERATORS and self.expected_value is not None:
            raise ValueError("unary operators cannot have expected_value")
        if self.operator is not None and self.operator not in _UNARY_OPERATORS:
            if self.expected_value is None:
                raise ValueError("comparison operators require expected_value")
        if self.operator is EligibilityOperator.BETWEEN:
            if not isinstance(self.expected_value, list) or len(self.expected_value) != 2:
                raise ValueError("between requires a two-item JSON array")
        if self.operator in {EligibilityOperator.IN, EligibilityOperator.NOT_IN}:
            if not isinstance(self.expected_value, list) or not self.expected_value:
                raise ValueError("membership operators require a non-empty JSON array")
        return self


class Scheme(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    jurisdiction: Jurisdiction
    categories: tuple[str, ...] = Field(min_length=1)
    summary: SourcedText
    benefits: tuple[SourcedText, ...]
    eligibility_rules: tuple[EligibilityRule, ...] = Field(min_length=1)
    required_documents: tuple[SourcedText, ...]
    application_steps: tuple[SourcedText, ...]
    official_sources: tuple[SourceReference, ...] = Field(min_length=1)
    publication_state: PublicationState
    version: SchemeVersion

    @model_validator(mode="after")
    def enforce_provenance(self) -> Scheme:
        sources = {source.source_id: source for source in self.official_sources}
        if len(sources) != len(self.official_sources):
            raise ValueError("official source IDs must be unique")
        rules = {rule.rule_id: rule for rule in self.eligibility_rules}
        if len(rules) != len(self.eligibility_rules):
            raise ValueError("eligibility rule IDs must be unique")
        if any(rule.scheme_id != self.scheme_id for rule in self.eligibility_rules):
            raise ValueError("eligibility rules must belong to their containing scheme")

        sourced_texts = (
            self.summary,
            *self.benefits,
            *self.required_documents,
            *self.application_steps,
        )
        referenced_ids = {source_id for item in sourced_texts for source_id in item.source_ref_ids}
        referenced_ids.update(rule.source_ref_id for rule in self.eligibility_rules)
        missing = referenced_ids.difference(sources)
        if missing:
            raise ValueError(f"scheme claims reference unknown sources: {sorted(missing)}")

        if self.publication_state is PublicationState.PUBLISHED:
            unapproved = {
                source_id
                for source_id in referenced_ids
                if sources[source_id].review_status is not SourceReviewStatus.APPROVED
            }
            if unapproved:
                raise ValueError(
                    f"published scheme claims require approved sources: {sorted(unapproved)}"
                )
        return self
