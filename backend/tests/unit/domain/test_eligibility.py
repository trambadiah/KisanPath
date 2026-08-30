from __future__ import annotations

import pytest
from pydantic import ValidationError

from kisanpath.domain.eligibility import (
    ConfidenceSummary,
    EvaluatorType,
    RuleEvaluation,
    RuleResult,
    SchemeEvaluation,
    SchemeStatus,
)


def evaluation(
    rule_id: str,
    result: RuleResult,
    *,
    evaluator: EvaluatorType = EvaluatorType.DETERMINISTIC,
    confidence: float | None = None,
) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        result=result,
        explanation="Synthetic deterministic result",
        source_ref_id="source-1",
        evaluator_type=evaluator,
        confidence=confidence,
    )


def test_deterministic_fail_cannot_be_overridden_by_eligible_status() -> None:
    failed = evaluation("rule-1", RuleResult.FAIL)
    with pytest.raises(ValidationError):
        SchemeEvaluation(
            scheme_id="scheme-1",
            status=SchemeStatus.LIKELY_ELIGIBLE,
            rule_evaluations=(failed,),
            blocking_rule_ids=("rule-1",),
        )


def test_not_eligible_requires_exact_blocking_rules() -> None:
    result = SchemeEvaluation(
        scheme_id="scheme-1",
        status=SchemeStatus.NOT_ELIGIBLE,
        rule_evaluations=(evaluation("rule-1", RuleResult.FAIL),),
        blocking_rule_ids=("rule-1",),
    )
    assert result.status is SchemeStatus.NOT_ELIGIBLE


def test_insufficient_information_requires_unknown_and_missing_field() -> None:
    with pytest.raises(ValidationError):
        SchemeEvaluation(
            scheme_id="scheme-1",
            status=SchemeStatus.INSUFFICIENT_INFORMATION,
            rule_evaluations=(evaluation("rule-1", RuleResult.UNKNOWN),),
        )


def test_manual_review_requires_matching_manual_rule() -> None:
    result = SchemeEvaluation(
        scheme_id="scheme-1",
        status=SchemeStatus.MANUAL_REVIEW,
        rule_evaluations=(
            evaluation("rule-1", RuleResult.MANUAL_REVIEW, evaluator=EvaluatorType.MANUAL),
        ),
        manual_review_rule_ids=("rule-1",),
    )
    assert result.status is SchemeStatus.MANUAL_REVIEW


def test_semantic_evaluation_requires_confidence() -> None:
    with pytest.raises(ValidationError):
        evaluation("rule-1", RuleResult.PASS, evaluator=EvaluatorType.SEMANTIC)


def test_confidence_summary_must_match_semantic_rules() -> None:
    semantic = evaluation(
        "rule-1", RuleResult.PASS, evaluator=EvaluatorType.SEMANTIC, confidence=0.8
    )
    with pytest.raises(ValidationError):
        SchemeEvaluation(
            scheme_id="scheme-1",
            status=SchemeStatus.LIKELY_ELIGIBLE,
            rule_evaluations=(semantic,),
            confidence_summary=ConfidenceSummary(
                semantic_rule_count=1, minimum_semantic_confidence=0.9
            ),
        )


def test_scheme_evaluation_round_trip_is_stable() -> None:
    original = SchemeEvaluation(
        scheme_id="scheme-1",
        status=SchemeStatus.LIKELY_ELIGIBLE,
        rule_evaluations=(evaluation("rule-1", RuleResult.PASS),),
    )
    assert SchemeEvaluation.model_validate_json(original.model_dump_json()) == original
