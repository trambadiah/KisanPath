from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from kisanpath.domain.conversation import (
    ConversationState,
    PendingConfirmation,
    WorkflowStage,
)
from kisanpath.domain.profile import LanguageCode
from kisanpath.domain.verification import (
    ClaimImportance,
    ClaimVerification,
    ClaimVerificationBatch,
    VerificationStatus,
)


def test_pending_confirmation_requires_confirmation_stage() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        ConversationState(
            conversation_id="conversation-1",
            preferred_language=LanguageCode.GUJARATI,
            pending_confirmation=PendingConfirmation(
                field="land_area",
                proposed_value="3 acres",
                source_message_id="message-1",
                prompt="Did you say three acres?",
            ),
            workflow_stage=WorkflowStage.UPDATE_PROFILE,
            created_at=now,
            updated_at=now,
        )


def test_conversation_rejects_time_reversal() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        ConversationState(
            conversation_id="conversation-1",
            preferred_language=LanguageCode.ENGLISH,
            created_at=now,
            updated_at=now - timedelta(seconds=1),
        )


def claim(status: VerificationStatus) -> ClaimVerification:
    return ClaimVerification(
        claim_id="claim-1",
        claim_text="Synthetic eligibility statement",
        importance=ClaimImportance.CONSEQUENTIAL,
        status=status,
        source_ref_ids=("source-1",) if status is VerificationStatus.SUPPORTED else (),
        explanation="Synthetic verification result",
    )


def test_consequential_supported_claim_is_publishable() -> None:
    batch = ClaimVerificationBatch(claims=(claim(VerificationStatus.SUPPORTED),))
    assert batch.publishable is True


@pytest.mark.parametrize(
    "status",
    [
        VerificationStatus.UNSUPPORTED,
        VerificationStatus.CONTRADICTED,
        VerificationStatus.UNCERTAIN,
    ],
)
def test_consequential_unverified_claim_is_not_publishable(
    status: VerificationStatus,
) -> None:
    batch = ClaimVerificationBatch(claims=(claim(status),))
    assert batch.publishable is False


def test_supported_claim_requires_provenance_or_rule() -> None:
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_id="claim-1",
            claim_text="Unsupported synthetic statement",
            importance=ClaimImportance.INFORMATIONAL,
            status=VerificationStatus.SUPPORTED,
            explanation="No evidence attached",
        )
