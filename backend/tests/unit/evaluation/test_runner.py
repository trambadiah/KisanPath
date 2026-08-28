from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from kisanpath.domain.profile import FarmerProfile
from kisanpath.evaluation.dataset import EvaluationDataset, EvaluationInput
from kisanpath.evaluation.runner import (
    EvaluationRunConfig,
    EvaluationRunner,
    WorkflowCaseOutput,
    WorkflowDescriptor,
    WorkflowKind,
)


class RecordingWorkflow:
    def __init__(self, kind: WorkflowKind) -> None:
        self._descriptor = WorkflowDescriptor(
            workflow_id=f"synthetic-{kind.value}", version="v1", kind=kind
        )
        self.inputs: list[EvaluationInput] = []

    @property
    def descriptor(self) -> WorkflowDescriptor:
        return self._descriptor

    async def run(self, case_input: EvaluationInput) -> WorkflowCaseOutput:
        self.inputs.append(case_input)
        return WorkflowCaseOutput(
            extracted_profile=FarmerProfile(),
            candidate_scheme_ids=(),
            scheme_evaluations=(),
        )


class FailingWorkflow(RecordingWorkflow):
    async def run(self, case_input: EvaluationInput) -> WorkflowCaseOutput:
        del case_input
        raise RetryableSyntheticError


class RetryableSyntheticError(RuntimeError):
    retryable = True


class CancelledWorkflow(RecordingWorkflow):
    async def run(self, case_input: EvaluationInput) -> WorkflowCaseOutput:
        del case_input
        raise asyncio.CancelledError


class TickClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 28, tzinfo=UTC)

    def __call__(self) -> datetime:
        current = self.value
        self.value += timedelta(seconds=1)
        return current


@pytest.fixture
def dataset() -> EvaluationDataset:
    from pathlib import Path

    from kisanpath.evaluation.dataset import load_evaluation_dataset

    path = Path(__file__).parents[4] / "data" / "evaluation" / "seed-cases.v1.json"
    return load_evaluation_dataset(path)


def runner() -> EvaluationRunner:
    return EvaluationRunner(clock=TickClock(), run_id_factory=lambda: "run-1")


def config() -> EvaluationRunConfig:
    return EvaluationRunConfig(corpus_version="synthetic-corpus-v1")


async def test_baseline_and_final_receive_identical_inputs_without_gold(
    dataset: EvaluationDataset,
) -> None:
    baseline = RecordingWorkflow(WorkflowKind.BASELINE)
    final = RecordingWorkflow(WorkflowKind.FINAL)

    await runner().run(dataset, baseline, config())
    await runner().run(dataset, final, config())

    expected_inputs = [case.input for case in dataset.cases]
    assert baseline.inputs == expected_inputs
    assert final.inputs == expected_inputs
    assert all(type(item) is EvaluationInput for item in baseline.inputs)


async def test_runner_returns_one_serializable_result_per_case(
    dataset: EvaluationDataset,
) -> None:
    run = await runner().run(dataset, RecordingWorkflow(WorkflowKind.BASELINE), config())

    assert len(run.results) == len(dataset.cases)
    assert all(result.output is not None and result.error is None for result in run.results)
    assert type(run).model_validate_json(run.model_dump_json()) == run


async def test_runner_records_owned_error_metadata_without_raw_message(
    dataset: EvaluationDataset,
) -> None:
    run = await runner().run(dataset, FailingWorkflow(WorkflowKind.BASELINE), config())

    assert all(result.output is None for result in run.results)
    assert all(result.error is not None for result in run.results)
    assert all(
        result.error.error_type == "RetryableSyntheticError"
        for result in run.results
        if result.error
    )
    assert all(result.error.retryable is True for result in run.results if result.error)


async def test_runner_propagates_cancellation(dataset: EvaluationDataset) -> None:
    with pytest.raises(asyncio.CancelledError):
        await runner().run(dataset, CancelledWorkflow(WorkflowKind.BASELINE), config())


def test_evaluation_fallback_defaults_off() -> None:
    assert config().fallback_enabled is False
