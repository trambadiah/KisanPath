"""Deterministic eligibility engine with a narrowly gated semantic evaluator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Protocol, cast

from pydantic import BaseModel, ConfigDict, Field
from pydantic.types import JsonValue

from kisanpath.domain.eligibility import (
    ConfidenceSummary,
    EligibilityOperator,
    EvaluatorType,
    RuleEvaluation,
    RuleResult,
    RuleType,
    SchemeEvaluation,
    SchemeStatus,
)
from kisanpath.domain.profile import FactStatus, FarmerProfile, ProfileFact
from kisanpath.domain.scheme import EligibilityRule, PublicationState, Scheme


class EligibilityEvaluationError(Exception):
    """Raised for invalid reviewed rule configuration, never farmer ineligibility."""


class SemanticRuleAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result: RuleResult
    explanation: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class SemanticEvaluationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: EligibilityRule
    profile: FarmerProfile
    approved_source_excerpt: str | None = Field(default=None, max_length=1000)


class SemanticRuleEvaluator(Protocol):
    async def evaluate(self, request: SemanticEvaluationRequest) -> SemanticRuleAssessment: ...


@dataclass(frozen=True)
class _ResolvedField:
    known: bool
    farmer_value: object | None
    normalized_value: object | None


class EligibilityEngine:
    """Evaluates reviewed rules; deterministic FAIL always wins aggregation."""

    def __init__(
        self,
        *,
        semantic_evaluator: SemanticRuleEvaluator | None = None,
        minimum_semantic_confidence: float = 0.7,
    ) -> None:
        if not 0 <= minimum_semantic_confidence <= 1:
            raise ValueError("minimum semantic confidence must be between zero and one")
        self._semantic_evaluator = semantic_evaluator
        self._minimum_semantic_confidence = minimum_semantic_confidence

    async def evaluate(self, scheme: Scheme, profile: FarmerProfile) -> SchemeEvaluation:
        if scheme.publication_state is not PublicationState.PUBLISHED:
            raise EligibilityEvaluationError("only published schemes may be evaluated")
        evaluations: list[RuleEvaluation] = []
        missing_fields: list[str] = []
        sources = {source.source_id: source for source in scheme.official_sources}
        for rule in scheme.eligibility_rules:
            if rule.rule_type is RuleType.DETERMINISTIC:
                evaluation, missing = self._evaluate_deterministic(rule, profile)
            elif rule.rule_type is RuleType.SEMANTIC:
                resolved = self._resolve(profile, rule.field) if rule.field else None
                if resolved is not None and not resolved.known:
                    evaluation, missing = self._unknown_semantic(rule, required=rule.required)
                else:
                    source = sources[rule.source_ref_id]
                    evaluation, missing = await self._evaluate_semantic(
                        rule,
                        profile,
                        source.bounded_excerpt,
                    )
            else:
                evaluation = RuleEvaluation(
                    rule_id=rule.rule_id,
                    result=RuleResult.MANUAL_REVIEW,
                    explanation="This reviewed rule explicitly requires manual review.",
                    source_ref_id=rule.source_ref_id,
                    evaluator_type=EvaluatorType.MANUAL,
                )
                missing = None
            evaluations.append(evaluation)
            if missing and missing not in missing_fields:
                missing_fields.append(missing)
        return self._aggregate(scheme.scheme_id, tuple(evaluations), tuple(missing_fields))

    def _evaluate_deterministic(
        self, rule: EligibilityRule, profile: FarmerProfile
    ) -> tuple[RuleEvaluation, str | None]:
        if rule.field is None or rule.operator is None:
            raise EligibilityEvaluationError(f"deterministic rule is incomplete: {rule.rule_id}")
        resolved = self._resolve(profile, rule.field)
        if not resolved.known:
            if not rule.required:
                return (
                    RuleEvaluation(
                        rule_id=rule.rule_id,
                        result=RuleResult.PASS,
                        explanation="Optional condition skipped because the fact is unknown.",
                        source_ref_id=rule.source_ref_id,
                        evaluator_type=EvaluatorType.DETERMINISTIC,
                    ),
                    None,
                )
            return (
                RuleEvaluation(
                    rule_id=rule.rule_id,
                    result=RuleResult.UNKNOWN,
                    farmer_value=self._to_json(resolved.farmer_value),
                    explanation=f"Required profile field is unknown: {rule.field}.",
                    source_ref_id=rule.source_ref_id,
                    evaluator_type=EvaluatorType.DETERMINISTIC,
                ),
                rule.field,
            )
        passed = self._compare(
            rule.operator,
            resolved.normalized_value,
            rule.expected_value,
            rule_id=rule.rule_id,
        )
        result = RuleResult.PASS if passed else RuleResult.FAIL
        return (
            RuleEvaluation(
                rule_id=rule.rule_id,
                result=result,
                farmer_value=self._to_json(resolved.farmer_value),
                normalized_value=self._to_json(resolved.normalized_value),
                explanation=(
                    f"Deterministic comparison {rule.field} {rule.operator.value} "
                    f"returned {result.value}."
                ),
                source_ref_id=rule.source_ref_id,
                evaluator_type=EvaluatorType.DETERMINISTIC,
            ),
            None,
        )

    def _unknown_semantic(
        self, rule: EligibilityRule, *, required: bool
    ) -> tuple[RuleEvaluation, str | None]:
        if not required:
            result = RuleResult.PASS
            missing = None
            explanation = "Optional semantic condition skipped because the fact is unknown."
        else:
            result = RuleResult.UNKNOWN
            missing = rule.field or f"semantic_context:{rule.rule_id}"
            explanation = "Semantic evaluation was not called because a required fact is unknown."
        return (
            RuleEvaluation(
                rule_id=rule.rule_id,
                result=result,
                explanation=explanation,
                source_ref_id=rule.source_ref_id,
                evaluator_type=EvaluatorType.SEMANTIC,
                confidence=0,
            ),
            missing,
        )

    async def _evaluate_semantic(
        self,
        rule: EligibilityRule,
        profile: FarmerProfile,
        source_excerpt: str | None,
    ) -> tuple[RuleEvaluation, str | None]:
        if self._semantic_evaluator is None:
            assessment = SemanticRuleAssessment(
                result=RuleResult.MANUAL_REVIEW,
                explanation="No semantic evaluator is configured for this semantic rule.",
                confidence=0,
            )
        else:
            assessment = await self._semantic_evaluator.evaluate(
                SemanticEvaluationRequest(
                    rule=rule,
                    profile=profile,
                    approved_source_excerpt=source_excerpt,
                )
            )
        result = assessment.result
        explanation = assessment.explanation
        if assessment.confidence < self._minimum_semantic_confidence:
            result = RuleResult.MANUAL_REVIEW
            explanation = "Semantic confidence is below the configured review threshold."
        missing = None
        if result is RuleResult.UNKNOWN:
            missing = rule.field or f"semantic_context:{rule.rule_id}"
        return (
            RuleEvaluation(
                rule_id=rule.rule_id,
                result=result,
                explanation=explanation,
                source_ref_id=rule.source_ref_id,
                evaluator_type=EvaluatorType.SEMANTIC,
                confidence=assessment.confidence,
            ),
            missing,
        )

    @staticmethod
    def _aggregate(
        scheme_id: str,
        evaluations: tuple[RuleEvaluation, ...],
        missing_fields: tuple[str, ...],
    ) -> SchemeEvaluation:
        failed = tuple(item.rule_id for item in evaluations if item.result is RuleResult.FAIL)
        manual = tuple(
            item.rule_id for item in evaluations if item.result is RuleResult.MANUAL_REVIEW
        )
        unknown = any(item.result is RuleResult.UNKNOWN for item in evaluations)
        if failed:
            status = SchemeStatus.NOT_ELIGIBLE
        elif manual:
            status = SchemeStatus.MANUAL_REVIEW
        elif unknown:
            status = SchemeStatus.INSUFFICIENT_INFORMATION
        else:
            status = SchemeStatus.LIKELY_ELIGIBLE
        semantic_confidences = tuple(
            item.confidence
            for item in evaluations
            if item.evaluator_type is EvaluatorType.SEMANTIC and item.confidence is not None
        )
        return SchemeEvaluation(
            scheme_id=scheme_id,
            status=status,
            rule_evaluations=evaluations,
            missing_fields=missing_fields,
            blocking_rule_ids=failed,
            manual_review_rule_ids=manual,
            confidence_summary=ConfidenceSummary(
                semantic_rule_count=len(semantic_confidences),
                minimum_semantic_confidence=(
                    min(semantic_confidences) if semantic_confidences else None
                ),
            ),
        )

    @staticmethod
    def _resolve(profile: FarmerProfile, field: str | None) -> _ResolvedField:
        if not field:
            return _ResolvedField(known=False, farmer_value=None, normalized_value=None)
        root, *nested = field.split(".")
        fact = getattr(profile, root, None)
        if not isinstance(fact, ProfileFact) or fact.status is not FactStatus.KNOWN:
            farmer_value: object | None = (
                fact.model_dump(mode="json") if isinstance(fact, ProfileFact) else None
            )
            return _ResolvedField(
                known=False,
                farmer_value=farmer_value,
                normalized_value=None,
            )
        value: object | None = fact.value
        farmer_value = value
        for part in nested:
            value = getattr(value, part, None)
            if value is None:
                return _ResolvedField(
                    known=False,
                    farmer_value=farmer_value,
                    normalized_value=None,
                )
        return _ResolvedField(known=True, farmer_value=farmer_value, normalized_value=value)

    @classmethod
    def _compare(
        cls,
        operator: EligibilityOperator,
        actual: object | None,
        expected: JsonValue,
        *,
        rule_id: str,
    ) -> bool:
        actual_value = actual.value if isinstance(actual, Enum) else actual
        if operator is EligibilityOperator.EQ:
            return actual_value == expected
        if operator is EligibilityOperator.NEQ:
            return actual_value != expected
        if operator in {EligibilityOperator.IN, EligibilityOperator.NOT_IN}:
            if not isinstance(expected, list):
                raise EligibilityEvaluationError(f"membership rule is invalid: {rule_id}")
            included = actual_value in expected
            return included if operator is EligibilityOperator.IN else not included
        if operator is EligibilityOperator.CONTAINS:
            try:
                return expected in actual_value  # type: ignore[operator]
            except TypeError as exc:
                raise EligibilityEvaluationError(
                    f"contains comparison is invalid: {rule_id}"
                ) from exc
        if operator is EligibilityOperator.BOOLEAN_TRUE:
            return actual_value is True
        if operator is EligibilityOperator.BOOLEAN_FALSE:
            return actual_value is False
        if operator is EligibilityOperator.EXISTS:
            return actual_value is not None
        if operator is EligibilityOperator.NOT_EXISTS:
            return actual_value is None
        try:
            actual_number = Decimal(str(actual_value))
            if operator is EligibilityOperator.BETWEEN:
                if not isinstance(expected, list) or len(expected) != 2:
                    raise EligibilityEvaluationError(f"range rule is invalid: {rule_id}")
                low, high = (Decimal(str(item)) for item in expected)
                return low <= actual_number <= high
            expected_number = Decimal(str(expected))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise EligibilityEvaluationError(f"numeric comparison is invalid: {rule_id}") from exc
        comparisons = {
            EligibilityOperator.LTE: actual_number <= expected_number,
            EligibilityOperator.LT: actual_number < expected_number,
            EligibilityOperator.GTE: actual_number >= expected_number,
            EligibilityOperator.GT: actual_number > expected_number,
        }
        if operator not in comparisons:
            raise EligibilityEvaluationError(f"unsupported operator: {operator.value}")
        return comparisons[operator]

    @staticmethod
    def _to_json(value: object | None) -> JsonValue:
        if value is None:
            return None
        if isinstance(value, BaseModel):
            return json.loads(value.model_dump_json())  # type: ignore[no-any-return]
        if isinstance(value, Enum):
            return cast(JsonValue, value.value)
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, tuple):
            return [EligibilityEngine._to_json(item) for item in value]
        return value  # type: ignore[return-value]
