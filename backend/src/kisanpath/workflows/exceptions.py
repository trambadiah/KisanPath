"""Workflow-owned failures suitable for later API normalization."""


class WorkflowError(Exception):
    """Base application workflow failure."""


class ConversationNotFoundError(WorkflowError):
    """Raised when a conversation ID is unknown."""


class InvalidWorkflowTransitionError(WorkflowError):
    """Raised when the explicit state machine would be violated."""
