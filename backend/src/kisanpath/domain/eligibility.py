"""Eligibility rule vocabulary and auditable evaluation outcomes."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.types import JsonValue


class RuleType(StrEnum):
    DETERMINISTIC = "deterministic"
    SEMANTIC = "semantic"
    MANUAL_REVIEW = "manual_review"


class EligibilityOperator(StrEnum):
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"
    LTE = "lte"
    LT = "lt"
    GTE = "gte"
    GT = "gt"
    BETWEEN = "between"
    CONTAINS = "contains"
    BOOLEAN_TRUE = "boolean_true"
    BOOLEAN_FALSE = "boolean_false"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class RuleResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class SchemeStatus(StrEnum):
    LIKELY_ELIGIBLE = "LIKELY_ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class EvaluatorType(StrEnum):
    DETERMINISTIC = "deterministic"
    SEMANTIC = "semantic"
    MANUAL = "manual"


class RuleEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str = Field(min_length=1)
    result: RuleResult
    farmer_value: JsonValue = None
    normalized_value: JsonValue = None
    explanation: str = Field(min_length=1, max_length=1000)
    source_ref_id: str = Field(min_length=1)
    evaluator_type: EvaluatorType
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_evaluator(self) -> RuleEvaluation:
        if self.evaluator_type is EvaluatorType.SEMANTIC and self.confidence is None:
            raise ValueError("semantic evaluations require confidence")
        if self.evaluator_type is not EvaluatorType.SEMANTIC and self.confidence is not None:
            raise ValueError("confidence is only valid for semantic evaluations")
        if (
            self.evaluator_type is EvaluatorType.DETERMINISTIC
            and self.result is RuleResult.MANUAL_REVIEW
        ):
            raise ValueError("deterministic evaluators cannot emit MANUAL_REVIEW")
        if (
            self.evaluator_type is EvaluatorType.MANUAL
            and self.result is not RuleResult.MANUAL_REVIEW
        ):
            raise ValueError("manual evaluators must emit MANUAL_REVIEW")
        return self


class ConfidenceSummary(BaseModel):
    """Aggregate metadata, never a replacement for individual rule results."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    semantic_rule_count: int = Field(default=0, ge=0)
    minimum_semantic_confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_count(self) -> ConfidenceSummary:
        if self.semantic_rule_count == 0 and self.minimum_semantic_confidence is not None:
            raise ValueError("confidence requires at least one semantic rule")
        if self.semantic_rule_count > 0 and self.minimum_semantic_confidence is None:
            raise ValueError("semantic rules require a minimum confidence")
        return self


class SchemeEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str = Field(min_length=1)
    status: SchemeStatus
    rule_evaluations: tuple[RuleEvaluation, ...] = Field(min_length=1)
    missing_fields: tuple[str, ...] = ()
    blocking_rule_ids: tuple[str, ...] = ()
    manual_review_rule_ids: tuple[str, ...] = ()
    confidence_summary: ConfidenceSummary = Field(default_factory=ConfidenceSummary)

    @model_validator(mode="after")
    def validate_aggregation(self) -> SchemeEvaluation:
        by_id = {evaluation.rule_id: evaluation for evaluation in self.rule_evaluations}
        if len(by_id) != len(self.rule_evaluations):
            raise ValueError("rule evaluations must have unique rule IDs")

        failed = {item.rule_id for item in self.rule_evaluations if item.result is RuleResult.FAIL}
        unknown = {
            item.rule_id
            for item in self.rule_evaluations
            if item.result is RuleResult.UNKNOWN
        }
        manual = {
            item.rule_id
            for item in self.rule_evaluations
            if item.result is RuleResult.MANUAL_REVIEW
        }
        if set(self.blocking_rule_ids) != failed:
            raise ValueError("blocking_rule_ids must exactly match FAIL rule evaluations")
        if set(self.manual_review_rule_ids) != manual:
            raise ValueError(
                "manual_review_rule_ids must exactly match MANUAL_REVIEW rule evaluations"
            )

        # This invariant is the hard boundary: no caller, including an LLM-backed
        # component, can represent a deterministic FAIL as an eligible status.
        if failed and self.status is not SchemeStatus.NOT_ELIGIBLE:
            raise ValueError("any FAIL requires NOT_ELIGIBLE")
        if self.status is SchemeStatus.NOT_ELIGIBLE and not failed:
            raise ValueError("NOT_ELIGIBLE requires a FAIL")
        if self.status is SchemeStatus.LIKELY_ELIGIBLE and (unknown or manual):
            raise ValueError("LIKELY_ELIGIBLE cannot contain unknown or manual rules")
        if unknown and not self.missing_fields:
            raise ValueError("UNKNOWN rule evaluations require missing_fields")
        if not unknown and self.missing_fields:
            raise ValueError("missing_fields require an UNKNOWN rule evaluation")
        if self.status is SchemeStatus.INSUFFICIENT_INFORMATION:
            if not unknown or manual:
                raise ValueError(
                    "INSUFFICIENT_INFORMATION requires unknown rules and no manual rules"
                )
        if self.status is SchemeStatus.MANUAL_REVIEW and not manual:
            raise ValueError("MANUAL_REVIEW requires a manual rule result")
        if manual and self.status not in {SchemeStatus.MANUAL_REVIEW, SchemeStatus.NOT_ELIGIBLE}:
            raise ValueError("manual rule results require manual review unless a FAIL blocks")

        semantic_rules = [
            item
            for item in self.rule_evaluations
            if item.evaluator_type is EvaluatorType.SEMANTIC
        ]
        semantic_confidences = [
            item.confidence
            for item in semantic_rules
            if item.confidence is not None
        ]
        expected_count = len(semantic_rules)
        expected_min = min(semantic_confidences) if semantic_confidences else None
        if self.confidence_summary.semantic_rule_count != expected_count:
            raise ValueError("confidence summary semantic count does not match rules")
        if self.confidence_summary.minimum_semantic_confidence != expected_min:
            raise ValueError("confidence summary minimum does not match rules")
        return self
