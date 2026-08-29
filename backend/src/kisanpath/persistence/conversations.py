"""In-memory canonical conversation repository for tests and local usage."""

from __future__ import annotations

from kisanpath.domain.conversation import ConversationState
from kisanpath.persistence.exceptions import (
    ConcurrentWriteError,
    RecordAlreadyExistsError,
)


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._states: dict[str, ConversationState] = {}

    async def add_conversation(self, state: ConversationState) -> None:
        if state.conversation_id in self._states:
            raise RecordAlreadyExistsError(f"conversation already exists: {state.conversation_id}")
        self._states[state.conversation_id] = state

    async def get_conversation(self, conversation_id: str) -> ConversationState | None:
        return self._states.get(conversation_id)

    async def save_conversation(self, state: ConversationState, *, expected_revision: int) -> None:
        current = self._states.get(state.conversation_id)
        if current is None:
            raise ConcurrentWriteError(f"conversation does not exist: {state.conversation_id}")
        if current.revision != expected_revision:
            raise ConcurrentWriteError(
                f"stale conversation revision for {state.conversation_id}: "
                f"expected {expected_revision}, found {current.revision}"
            )
        self._states[state.conversation_id] = state
