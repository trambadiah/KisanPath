"""Transport-neutral workflow observation boundary."""

from __future__ import annotations

from typing import Protocol

from kisanpath.domain.conversation import WorkflowStage


class WorkflowObserver(Protocol):
    def transition(
        self,
        *,
        conversation_id: str,
        from_stage: WorkflowStage,
        to_stage: WorkflowStage,
    ) -> None: ...


class NoopWorkflowObserver:
    def transition(
        self,
        *,
        conversation_id: str,
        from_stage: WorkflowStage,
        to_stage: WorkflowStage,
    ) -> None:
        del conversation_id, from_stage, to_stage
