"""Versioned, frozen synthetic evaluation-case schema."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from kisanpath.domain.eligibility import RuleResult, SchemeStatus
from kisanpath.domain.profile import FarmerProfile, LanguageCode


class EvaluationDatasetError(ValueError):
    pass


class EvaluationTag(StrEnum):
    LIKELY_ELIGIBLE = "likely_eligible"
    NOT_ELIGIBLE = "not_eligible"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    MANUAL_REVIEW = "manual_review"
    AMBIGUOUS_LAND_UNIT = "ambiguous_land_unit"
    MULTILINGUAL = "multilingual"
    CODE_SWITCHING = "code_switching"
    CONFLICTING_PROFILE = "conflicting_profile"


class EvaluationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    utterance: str = Field(min_length=1, max_length=4000)
    language_hint: LanguageCode = LanguageCode.UNDETERMINED
    input_mode: Literal["text", "voice_transcript"] = "text"


class ExpectedRuleOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str = Field(min_length=1)
    result: RuleResult


class ExpectedSchemeOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme_id: str = Field(min_length=1)
    status: SchemeStatus
    rule_outcomes: tuple[ExpectedRuleOutcome, ...] = Field(min_length=1)
    missing_fields: tuple[str, ...] = ()
    blocking_rule_ids: tuple[str, ...] = ()
    manual_review_rule_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_gold_aggregation(self) -> ExpectedSchemeOutcome:
        by_id = {outcome.rule_id: outcome for outcome in self.rule_outcomes}
        if len(by_id) != len(self.rule_outcomes):
            raise ValueError("gold rule IDs must be unique per scheme")
        failed = {item.rule_id for item in self.rule_outcomes if item.result is RuleResult.FAIL}
        unknown = {item.rule_id for item in self.rule_outcomes if item.result is RuleResult.UNKNOWN}
        manual = {
            item.rule_id for item in self.rule_outcomes if item.result is RuleResult.MANUAL_REVIEW
        }
        if set(self.blocking_rule_ids) != failed:
            raise ValueError("gold blocking_rule_ids must exactly match FAIL outcomes")
        if set(self.manual_review_rule_ids) != manual:
            raise ValueError("gold manual_review_rule_ids must match manual outcomes")
        if failed and self.status is not SchemeStatus.NOT_ELIGIBLE:
            raise ValueError("gold FAIL always requires NOT_ELIGIBLE")
        if self.status is SchemeStatus.NOT_ELIGIBLE and not failed:
            raise ValueError("gold NOT_ELIGIBLE requires a FAIL")
        if self.status is SchemeStatus.LIKELY_ELIGIBLE and (failed or unknown or manual):
            raise ValueError("gold likely-eligible outcomes must all pass")
        if unknown and not self.missing_fields:
            raise ValueError("gold UNKNOWN outcomes require missing fields")
        if not unknown and self.missing_fields:
            raise ValueError("gold missing fields require UNKNOWN outcomes")
        if self.status is SchemeStatus.INSUFFICIENT_INFORMATION and (not unknown or manual):
            raise ValueError(
                "gold insufficient information requires unknowns and no manual outcomes"
            )
        if self.status is SchemeStatus.MANUAL_REVIEW and not manual:
            raise ValueError("gold manual review requires a manual rule outcome")
        return self


class EvaluationCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]+$")
    title: str = Field(min_length=1)
    synthetic: Literal[True] = True
    tags: frozenset[EvaluationTag] = Field(min_length=1)
    input: EvaluationInput
    expected_profile: FarmerProfile
    expected_relevant_scheme_ids: tuple[str, ...] = Field(min_length=1)
    expected_scheme_outcomes: tuple[ExpectedSchemeOutcome, ...] = Field(min_length=1)
    audit_note: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_expectations(self) -> EvaluationCase:
        relevant = set(self.expected_relevant_scheme_ids)
        if len(relevant) != len(self.expected_relevant_scheme_ids):
            raise ValueError("expected relevant scheme IDs must be unique")
        outcome_ids = [outcome.scheme_id for outcome in self.expected_scheme_outcomes]
        if len(outcome_ids) != len(set(outcome_ids)):
            raise ValueError("expected scheme outcomes must be unique")
        if not set(outcome_ids).issubset(relevant):
            raise ValueError("scheme outcomes must be included in relevant scheme IDs")
        return self


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"]
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    frozen: Literal[True]
    synthetic_only: Literal[True]
    created_at: datetime
    cases: tuple[EvaluationCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dataset(self) -> EvaluationDataset:
        if self.created_at.tzinfo is None:
            raise ValueError("dataset created_at must be timezone-aware")
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("evaluation case IDs must be unique")
        return self


def load_evaluation_dataset(path: str | Path) -> EvaluationDataset:
    resolved = Path(path)
    try:
        raw = resolved.read_bytes()
        checksum_path = Path(f"{resolved}.sha256")
        if checksum_path.exists():
            checksum_parts = checksum_path.read_text(encoding="utf-8").split()
            if not checksum_parts or len(checksum_parts[0]) != 64:
                raise EvaluationDatasetError(
                    f"Invalid evaluation dataset checksum file: {checksum_path}"
                )
            expected_checksum = checksum_parts[0]
            actual_checksum = sha256(raw).hexdigest()
            if actual_checksum != expected_checksum:
                raise EvaluationDatasetError(
                    f"Frozen evaluation dataset checksum mismatch: {resolved}"
                )
        payload = json.loads(raw)
        return EvaluationDataset.model_validate(payload)
    except EvaluationDatasetError:
        raise
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise EvaluationDatasetError(f"Invalid evaluation dataset: {resolved}") from exc
