from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from kisanpath.domain.eligibility import (
    EligibilityOperator,
    RuleResult,
    RuleType,
    SchemeStatus,
)
from kisanpath.domain.eligibility_engine import (
    EligibilityEngine,
    SemanticEvaluationRequest,
    SemanticRuleAssessment,
)
from kisanpath.domain.profile import (
    FactStatus,
    FarmerProfile,
    LandUnit,
    ProfileFact,
    normalize_land_area,
)
from kisanpath.domain.scheme import (
    EligibilityRule,
    Jurisdiction,
    PublicationState,
    Scheme,
    SchemeVersion,
    SourcedText,
    SourceReference,
    SourceReviewStatus,
)


class RecordingSemanticEvaluator:
    def __init__(self, result: RuleResult = RuleResult.PASS, confidence: float = 0.95) -> None:
        self.result = result
        self.confidence = confidence
        self.calls: list[SemanticEvaluationRequest] = []

    async def evaluate(self, request: SemanticEvaluationRequest) -> SemanticRuleAssessment:
        self.calls.append(request)
        return SemanticRuleAssessment(
            result=self.result,
            confidence=self.confidence,
            explanation="Synthetic semantic assessment.",
        )


def _scheme(*rules: EligibilityRule) -> Scheme:
    source = SourceReference(
        source_id="source-1",
        document_id="document-1",
        source_locator="synthetic://eligibility-engine",
        title="Synthetic eligibility source",
        locator="section-1",
        imported_at=datetime(2026, 8, 29, tzinfo=UTC),
        review_status=SourceReviewStatus.APPROVED,
        bounded_excerpt="A fictional reviewed eligibility condition.",
    )
    sourced = SourcedText(text="Synthetic scheme.", source_ref_ids=(source.source_id,))
    return Scheme(
        scheme_id="scheme-1",
        name="Synthetic Scheme",
        authority="Synthetic Authority",
        jurisdiction=Jurisdiction(states=("Gujarat",)),
        categories=("synthetic",),
        summary=sourced,
        benefits=(),
        eligibility_rules=rules,
        required_documents=(),
        application_steps=(),
        official_sources=(source,),
        publication_state=PublicationState.PUBLISHED,
        version=SchemeVersion(
            version_id="v1",
            effective_from=date(2026, 1, 1),
            corpus_version="synthetic-v1",
        ),
    )


def _rule(
    operator: EligibilityOperator,
    expected: Any,
    *,
    rule_id: str = "rule-1",
    field: str = "land_area.normalized_hectares",
) -> EligibilityRule:
    return EligibilityRule(
        rule_id=rule_id,
        scheme_id="scheme-1",
        description="Synthetic deterministic condition.",
        rule_type=RuleType.DETERMINISTIC,
        field=field,
        operator=operator,
        expected_value=expected,
        source_ref_id="source-1",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operator", "expected", "status"),
    [
        (EligibilityOperator.LTE, 2, SchemeStatus.LIKELY_ELIGIBLE),
        (EligibilityOperator.GT, 2, SchemeStatus.NOT_ELIGIBLE),
        (EligibilityOperator.BETWEEN, [1, 2], SchemeStatus.LIKELY_ELIGIBLE),
    ],
)
async def test_numeric_operators_are_deterministic(
    operator: EligibilityOperator,
    expected: Any,
    status: SchemeStatus,
) -> None:
    profile = FarmerProfile(
        land_area=ProfileFact(
            status=FactStatus.KNOWN,
            value=normalize_land_area(Decimal("1.5"), LandUnit.HECTARE),
        )
    )

    result = await EligibilityEngine().evaluate(_scheme(_rule(operator, expected)), profile)

    assert result.status is status


@pytest.mark.asyncio
async def test_semantic_evaluator_is_never_called_for_deterministic_rule() -> None:
    semantic = RecordingSemanticEvaluator()
    profile = FarmerProfile(
        land_area=ProfileFact(
            status=FactStatus.KNOWN,
            value=normalize_land_area(3, LandUnit.HECTARE),
        )
    )

    result = await EligibilityEngine(semantic_evaluator=semantic).evaluate(
        _scheme(_rule(EligibilityOperator.LTE, 2)), profile
    )

    assert result.status is SchemeStatus.NOT_ELIGIBLE
    assert semantic.calls == []


@pytest.mark.asyncio
async def test_missing_required_fact_remains_unknown() -> None:
    result = await EligibilityEngine().evaluate(
        _scheme(_rule(EligibilityOperator.LTE, 2)),
        FarmerProfile(),
    )

    assert result.status is SchemeStatus.INSUFFICIENT_INFORMATION
    assert result.rule_evaluations[0].result is RuleResult.UNKNOWN
    assert result.missing_fields == ("land_area.normalized_hectares",)


@pytest.mark.asyncio
async def test_low_confidence_semantic_result_routes_to_manual_review() -> None:
    semantic = RecordingSemanticEvaluator(confidence=0.3)
    semantic_rule = EligibilityRule(
        rule_id="semantic-rule",
        scheme_id="scheme-1",
        description="Synthetic non-structurable condition.",
        rule_type=RuleType.SEMANTIC,
        source_ref_id="source-1",
    )

    result = await EligibilityEngine(
        semantic_evaluator=semantic,
        minimum_semantic_confidence=0.7,
    ).evaluate(_scheme(semantic_rule), FarmerProfile())

    assert result.status is SchemeStatus.MANUAL_REVIEW
    assert result.rule_evaluations[0].result is RuleResult.MANUAL_REVIEW
