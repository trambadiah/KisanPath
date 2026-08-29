"""Deterministic minimum-next-question selection."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from kisanpath.domain.eligibility import RuleResult, SchemeEvaluation


class ClarificationNeed(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(min_length=1)
    affected_scheme_ids: tuple[str, ...] = Field(min_length=1)
    affected_rule_ids: tuple[str, ...] = Field(min_length=1)


class ClarificationPolicy:
    """Prefers a required missing fact affecting the most candidate rules."""

    _critical_priority = {
        "state": 0,
        "district": 1,
        "land_area.normalized_hectares": 2,
        "land_area": 2,
        "land_ownership": 3,
    }

    def choose(self, evaluations: tuple[SchemeEvaluation, ...]) -> ClarificationNeed | None:
        schemes_by_field: dict[str, set[str]] = defaultdict(set)
        rules_by_field: dict[str, set[str]] = defaultdict(set)
        for evaluation in evaluations:
            unknown_rules = {
                item.rule_id
                for item in evaluation.rule_evaluations
                if item.result is RuleResult.UNKNOWN
            }
            for field in evaluation.missing_fields:
                schemes_by_field[field].add(evaluation.scheme_id)
                rules_by_field[field].update(unknown_rules)
        if not schemes_by_field:
            return None
        field = min(
            schemes_by_field,
            key=lambda item: (
                -len(schemes_by_field[item]),
                self._critical_priority.get(item, 100),
                item,
            ),
        )
        return ClarificationNeed(
            field=field,
            affected_scheme_ids=tuple(sorted(schemes_by_field[field])),
            affected_rule_ids=tuple(sorted(rules_by_field[field])),
        )
