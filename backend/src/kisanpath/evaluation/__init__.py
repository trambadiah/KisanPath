"""Evaluation schemas and API-independent runner contracts."""

from kisanpath.evaluation.dataset import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationDatasetError,
    EvaluationInput,
    EvaluationTag,
    ExpectedRuleOutcome,
    ExpectedSchemeOutcome,
    load_evaluation_dataset,
)
from kisanpath.evaluation.runner import (
    CaseExecutionError,
    CaseExecutionResult,
    EvaluationRun,
    EvaluationRunConfig,
    EvaluationRunner,
    EvaluationUsage,
    EvaluationWorkflow,
    WorkflowCaseOutput,
    WorkflowDescriptor,
    WorkflowKind,
)

__all__ = [
    "CaseExecutionError",
    "CaseExecutionResult",
    "EvaluationCase",
    "EvaluationDataset",
    "EvaluationDatasetError",
    "EvaluationInput",
    "EvaluationRun",
    "EvaluationRunConfig",
    "EvaluationRunner",
    "EvaluationTag",
    "EvaluationUsage",
    "EvaluationWorkflow",
    "ExpectedRuleOutcome",
    "ExpectedSchemeOutcome",
    "WorkflowCaseOutput",
    "WorkflowDescriptor",
    "WorkflowKind",
    "load_evaluation_dataset",
]
