"""Small runner boundary shared by future baseline and final workflows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kisanpath.domain.eligibility import SchemeEvaluation
from kisanpath.domain.profile import FarmerProfile
from kisanpath.domain.verification import ClaimVerificationBatch
from kisanpath.evaluation.dataset import EvaluationDataset, EvaluationInput


class WorkflowKind(StrEnum):
    BASELINE = "baseline"
    FINAL = "final"


class WorkflowDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workflow_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    kind: WorkflowKind


class EvaluationUsage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)


class WorkflowCaseOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    extracted_profile: FarmerProfile
    candidate_scheme_ids: tuple[str, ...]
    scheme_evaluations: tuple[SchemeEvaluation, ...]
    claim_verifications: ClaimVerificationBatch = Field(default_factory=ClaimVerificationBatch)
    response_text: str | None = None
    usage: EvaluationUsage = Field(default_factory=EvaluationUsage)
    provider_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_output(self) -> WorkflowCaseOutput:
        if len(self.candidate_scheme_ids) != len(set(self.candidate_scheme_ids)):
            raise ValueError("candidate scheme IDs must be unique")
        scheme_ids = [item.scheme_id for item in self.scheme_evaluations]
        if len(scheme_ids) != len(set(scheme_ids)):
            raise ValueError("scheme evaluations must be unique")
        return self


class EvaluationWorkflow(Protocol):
    @property
    def descriptor(self) -> WorkflowDescriptor: ...

    async def run(self, case_input: EvaluationInput) -> WorkflowCaseOutput: ...


class EvaluationRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    corpus_version: str = Field(min_length=1)
    provider: str | None = None
    model: str | None = None
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    fallback_enabled: bool = False
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class CaseExecutionError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    error_type: str = Field(min_length=1)
    retryable: bool = False


class CaseExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    latency_ms: float = Field(ge=0)
    output: WorkflowCaseOutput | None = None
    error: CaseExecutionError | None = None

    @model_validator(mode="after")
    def require_one_result(self) -> CaseExecutionResult:
        if (self.output is None) == (self.error is None):
            raise ValueError("case result requires exactly one of output or error")
        return self


class EvaluationRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    workflow: WorkflowDescriptor
    dataset_id: str
    dataset_version: str
    config: EvaluationRunConfig
    started_at: datetime
    completed_at: datetime
    results: tuple[CaseExecutionResult, ...]

    @model_validator(mode="after")
    def validate_run(self) -> EvaluationRun:
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("evaluation timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        result_ids = [result.case_id for result in self.results]
        if len(result_ids) != len(set(result_ids)):
            raise ValueError("evaluation results must have unique case IDs")
        return self


class EvaluationRunner:
    """Executes a workflow without exposing frozen gold labels to it."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._run_id_factory = run_id_factory or (lambda: str(uuid4()))

    async def run(
        self,
        dataset: EvaluationDataset,
        workflow: EvaluationWorkflow,
        config: EvaluationRunConfig,
    ) -> EvaluationRun:
        started_at = self._clock()
        results: list[CaseExecutionResult] = []
        for case in dataset.cases:
            started = perf_counter()
            try:
                # Intentionally pass only input. Expected profile/rules/statuses
                # remain runner-owned gold data and cannot leak into workflows.
                output = await workflow.run(case.input)
                result = CaseExecutionResult(
                    case_id=case.case_id,
                    latency_ms=(perf_counter() - started) * 1000,
                    output=output,
                )
            except Exception as exc:
                result = CaseExecutionResult(
                    case_id=case.case_id,
                    latency_ms=(perf_counter() - started) * 1000,
                    error=CaseExecutionError(
                        error_type=type(exc).__name__,
                        retryable=bool(getattr(exc, "retryable", False)),
                    ),
                )
            results.append(result)
        return EvaluationRun(
            run_id=self._run_id_factory(),
            workflow=workflow.descriptor,
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            config=config,
            started_at=started_at,
            completed_at=self._clock(),
            results=tuple(results),
        )
