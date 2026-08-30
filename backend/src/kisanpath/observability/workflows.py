"""Low-cardinality metrics adapter for workflow transition events."""

from __future__ import annotations

from kisanpath.domain.conversation import WorkflowStage
from kisanpath.observability.metrics import MetricsSink


class MetricsWorkflowObserver:
    def __init__(self, metrics: MetricsSink) -> None:
        self._metrics = metrics

    def transition(
        self,
        *,
        conversation_id: str,
        from_stage: WorkflowStage,
        to_stage: WorkflowStage,
    ) -> None:
        del conversation_id
        self._metrics.increment(
            "kisanpath_workflow_transitions_total",
            labels={"stage": to_stage.value, "reason": from_stage.value},
        )
