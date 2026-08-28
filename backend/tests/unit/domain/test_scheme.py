from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from kisanpath.domain.eligibility import EligibilityOperator, RuleType
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


def source(status: SourceReviewStatus = SourceReviewStatus.APPROVED) -> SourceReference:
    return SourceReference(
        source_id="source-1",
        document_id="document-1",
        source_locator="synthetic://scheme/document-1",
        title="Synthetic reviewed scheme fixture",
        locator="section-1",
        imported_at=datetime(2026, 8, 28, tzinfo=UTC),
        review_status=status,
    )


def rule(*, scheme_id: str = "scheme-1") -> EligibilityRule:
    return EligibilityRule(
        rule_id="rule-1",
        scheme_id=scheme_id,
        description="State must be Gujarat",
        rule_type=RuleType.DETERMINISTIC,
        field="state",
        operator=EligibilityOperator.EQ,
        expected_value="Gujarat",
        required=True,
        source_ref_id="source-1",
    )


def scheme(
    *,
    review_status: SourceReviewStatus = SourceReviewStatus.APPROVED,
    eligibility_rule: EligibilityRule | None = None,
) -> Scheme:
    sourced = SourcedText(text="Synthetic claim", source_ref_ids=("source-1",))
    return Scheme(
        scheme_id="scheme-1",
        name="Synthetic Scheme",
        authority="Synthetic Authority",
        jurisdiction=Jurisdiction(states=("Gujarat",)),
        categories=("irrigation",),
        summary=sourced,
        benefits=(sourced,),
        eligibility_rules=(eligibility_rule or rule(),),
        required_documents=(sourced,),
        application_steps=(sourced,),
        official_sources=(source(review_status),),
        publication_state=PublicationState.PUBLISHED,
        version=SchemeVersion(
            version_id="v1",
            effective_from=date(2026, 1, 1),
            corpus_version="synthetic-v1",
        ),
    )


def test_published_scheme_with_approved_provenance_validates() -> None:
    restored = Scheme.model_validate_json(scheme().model_dump_json())
    assert restored.scheme_id == "scheme-1"


def test_published_scheme_rejects_unapproved_claim_sources() -> None:
    with pytest.raises(ValidationError):
        scheme(review_status=SourceReviewStatus.PENDING)


def test_scheme_rejects_rule_owned_by_another_scheme() -> None:
    with pytest.raises(ValidationError):
        scheme(eligibility_rule=rule(scheme_id="other-scheme"))


def test_source_requires_stable_location() -> None:
    with pytest.raises(ValidationError):
        SourceReference(
            source_id="source-1",
            document_id="document-1",
            title="Missing location",
            locator="section-1",
            imported_at=datetime.now(UTC),
            review_status=SourceReviewStatus.APPROVED,
        )


def test_deterministic_rule_requires_operator_and_field() -> None:
    with pytest.raises(ValidationError):
        EligibilityRule(
            rule_id="rule-1",
            scheme_id="scheme-1",
            description="Incomplete deterministic rule",
            rule_type=RuleType.DETERMINISTIC,
            source_ref_id="source-1",
        )


def test_between_operator_requires_two_values() -> None:
    with pytest.raises(ValidationError):
        EligibilityRule(
            rule_id="rule-1",
            scheme_id="scheme-1",
            description="Invalid range",
            rule_type=RuleType.DETERMINISTIC,
            field="land_area.normalized_hectares",
            operator=EligibilityOperator.BETWEEN,
            expected_value=[1],
            source_ref_id="source-1",
        )


def test_nationwide_jurisdiction_cannot_list_states() -> None:
    with pytest.raises(ValidationError):
        Jurisdiction(nationwide=True, states=("Gujarat",))
