from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kisanpath.domain.conversation import ConversationState, WorkflowStage, WorkflowTransition
from kisanpath.domain.profile import LanguageCode
from kisanpath.persistence.conversations import InMemoryConversationRepository
from kisanpath.persistence.exceptions import ConcurrentWriteError


@pytest.mark.asyncio
async def test_conversation_repository_persists_canonical_state_and_revision() -> None:
    now = datetime(2026, 8, 29, tzinfo=UTC)
    repository = InMemoryConversationRepository()
    original = ConversationState(
        conversation_id="conversation-1",
        preferred_language=LanguageCode.ENGLISH,
        created_at=now,
        updated_at=now,
    )
    await repository.add_conversation(original)
    updated = ConversationState(
        conversation_id=original.conversation_id,
        preferred_language=original.preferred_language,
        workflow_stage=WorkflowStage.PARSE_INPUT,
        created_at=now,
        updated_at=now,
        revision=1,
        transitions=(
            WorkflowTransition(
                from_stage=WorkflowStage.START,
                to_stage=WorkflowStage.PARSE_INPUT,
                occurred_at=now,
                revision=1,
                trigger_message_id="message-1",
            ),
        ),
    )

    await repository.save_conversation(updated, expected_revision=0)

    assert await repository.get_conversation(original.conversation_id) == updated


@pytest.mark.asyncio
async def test_conversation_repository_rejects_stale_write() -> None:
    now = datetime(2026, 8, 29, tzinfo=UTC)
    repository = InMemoryConversationRepository()
    state = ConversationState(
        conversation_id="conversation-stale",
        preferred_language=LanguageCode.ENGLISH,
        created_at=now,
        updated_at=now,
    )
    await repository.add_conversation(state)

    with pytest.raises(ConcurrentWriteError, match="stale conversation revision"):
        await repository.save_conversation(state, expected_revision=1)
