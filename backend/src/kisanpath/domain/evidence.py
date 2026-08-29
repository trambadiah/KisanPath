"""Deterministic verification of eligibility claims against reviewed provenance."""

from __future__ import annotations

from kisanpath.domain.eligibility import SchemeEvaluation
from kisanpath.domain.scheme import Scheme, SourceReviewStatus
from kisanpath.domain.verification import (
    ClaimImportance,
    ClaimVerification,
    ClaimVerificationBatch,
    VerificationStatus,
)


class EvidenceVerifier:
    """Verifies existing rule results; it never recomputes eligibility."""

    def verify(
        self,
        schemes: tuple[Scheme, ...],
        evaluations: tuple[SchemeEvaluation, ...],
    ) -> ClaimVerificationBatch:
        scheme_by_id = {scheme.scheme_id: scheme for scheme in schemes}
        claims: list[ClaimVerification] = []
        for evaluation in evaluations:
            scheme = scheme_by_id.get(evaluation.scheme_id)
            if scheme is None:
                claims.append(self._unsupported_overall(evaluation))
                continue
            rules = {rule.rule_id: rule for rule in scheme.eligibility_rules}
            sources = {source.source_id: source for source in scheme.official_sources}
            supported_rule_ids: list[str] = []
            supported_source_ids: list[str] = []
            for rule_evaluation in evaluation.rule_evaluations:
                rule = rules.get(rule_evaluation.rule_id)
                source = sources.get(rule_evaluation.source_ref_id)
                supported = (
                    rule is not None
                    and rule.source_ref_id == rule_evaluation.source_ref_id
                    and source is not None
                    and source.review_status is SourceReviewStatus.APPROVED
                )
                if supported:
                    supported_rule_ids.append(rule_evaluation.rule_id)
                    supported_source_ids.append(rule_evaluation.source_ref_id)
                claims.append(
                    ClaimVerification(
                        claim_id=f"{evaluation.scheme_id}:rule:{rule_evaluation.rule_id}",
                        claim_text=rule_evaluation.explanation,
                        importance=ClaimImportance.CONSEQUENTIAL,
                        status=(
                            VerificationStatus.SUPPORTED
                            if supported
                            else VerificationStatus.UNSUPPORTED
                        ),
                        source_ref_ids=(rule_evaluation.source_ref_id,) if supported else (),
                        derived_rule_ids=(rule_evaluation.rule_id,) if supported else (),
                        explanation=(
                            "Rule result maps to a reviewed rule and approved source."
                            if supported
                            else "Rule result could not be mapped to approved provenance."
                        ),
                    )
                )
            overall_supported = len(supported_rule_ids) == len(evaluation.rule_evaluations)
            claims.append(
                ClaimVerification(
                    claim_id=f"{evaluation.scheme_id}:overall",
                    claim_text=f"{scheme.name}: {evaluation.status.value}",
                    importance=ClaimImportance.CONSEQUENTIAL,
                    status=(
                        VerificationStatus.SUPPORTED
                        if overall_supported
                        else VerificationStatus.UNSUPPORTED
                    ),
                    source_ref_ids=(
                        tuple(dict.fromkeys(supported_source_ids)) if overall_supported else ()
                    ),
                    derived_rule_ids=(tuple(supported_rule_ids) if overall_supported else ()),
                    explanation=(
                        "Overall status derives from verified reviewed rule results."
                        if overall_supported
                        else "At least one consequential rule result lacks approved provenance."
                    ),
                )
            )
        return ClaimVerificationBatch(claims=tuple(claims))

    @staticmethod
    def _unsupported_overall(evaluation: SchemeEvaluation) -> ClaimVerification:
        return ClaimVerification(
            claim_id=f"{evaluation.scheme_id}:overall",
            claim_text=f"{evaluation.scheme_id}: {evaluation.status.value}",
            importance=ClaimImportance.CONSEQUENTIAL,
            status=VerificationStatus.UNSUPPORTED,
            explanation="The evaluated scheme is absent from approved retrieval evidence.",
        )
