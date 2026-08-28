from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from kisanpath.domain.eligibility import RuleResult, SchemeStatus
from kisanpath.evaluation.dataset import (
    EvaluationDatasetError,
    EvaluationTag,
    ExpectedRuleOutcome,
    ExpectedSchemeOutcome,
    load_evaluation_dataset,
)

DATASET_PATH = Path(__file__).parents[4] / "data" / "evaluation" / "seed-cases.v1.json"


def test_frozen_seed_dataset_loads_and_has_required_coverage() -> None:
    dataset = load_evaluation_dataset(DATASET_PATH)
    tags = {tag for case in dataset.cases for tag in case.tags}

    assert dataset.frozen is True
    assert dataset.synthetic_only is True
    assert len(dataset.cases) == 6
    assert {
        EvaluationTag.LIKELY_ELIGIBLE,
        EvaluationTag.NOT_ELIGIBLE,
        EvaluationTag.INSUFFICIENT_INFORMATION,
        EvaluationTag.MANUAL_REVIEW,
        EvaluationTag.AMBIGUOUS_LAND_UNIT,
        EvaluationTag.MULTILINGUAL,
    }.issubset(tags)


def test_seed_dataset_covers_all_gold_statuses() -> None:
    dataset = load_evaluation_dataset(DATASET_PATH)
    statuses = {
        outcome.status
        for case in dataset.cases
        for outcome in case.expected_scheme_outcomes
    }
    assert statuses == set(SchemeStatus)


def test_frozen_seed_checksum_matches_fixture_bytes() -> None:
    checksum_path = Path(f"{DATASET_PATH}.sha256")
    expected = checksum_path.read_text(encoding="utf-8").split()[0]
    assert sha256(DATASET_PATH.read_bytes()).hexdigest() == expected


def test_seed_dataset_contains_no_obvious_personal_identifiers() -> None:
    raw = DATASET_PATH.read_text(encoding="utf-8")

    assert "aadhaar" not in raw.lower()
    assert not re.search(r"\b\d{12}\b", raw)
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", raw)
    assert not re.search(r"(?<!\d)[6-9]\d{9}(?!\d)", raw)


def test_seed_case_ids_are_not_hardcoded_in_application_code() -> None:
    dataset = load_evaluation_dataset(DATASET_PATH)
    source_root = Path(__file__).parents[3] / "src" / "kisanpath"
    application_source = "\n".join(
        path.read_text(encoding="utf-8") for path in source_root.rglob("*.py")
    )

    for case in dataset.cases:
        assert case.case_id not in application_source


def test_gold_fail_cannot_be_labeled_likely_eligible() -> None:
    with pytest.raises(ValidationError):
        ExpectedSchemeOutcome(
            scheme_id="synthetic-scheme",
            status=SchemeStatus.LIKELY_ELIGIBLE,
            rule_outcomes=(
                ExpectedRuleOutcome(rule_id="blocking-rule", result=RuleResult.FAIL),
            ),
            blocking_rule_ids=("blocking-rule",),
        )


def test_invalid_dataset_file_maps_to_owned_error(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(EvaluationDatasetError):
        load_evaluation_dataset(invalid)


def test_dataset_round_trip_is_stable() -> None:
    dataset = load_evaluation_dataset(DATASET_PATH)
    restored = type(dataset).model_validate_json(dataset.model_dump_json())
    assert restored == dataset
