"""First complete, persistent, text-based KisanPath vertical slice."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from kisanpath.agents.profile import ProfileExtractionRequest, ProfileExtractor
from kisanpath.domain.clarification import ClarificationPolicy
from kisanpath.domain.conversation import (
    ConversationState,
    PendingClarification,
    PendingConfirmation,
    WorkflowStage,
    WorkflowTransition,
)
from kisanpath.domain.eligibility_engine import EligibilityEngine
from kisanpath.domain.evidence import EvidenceVerifier
from kisanpath.domain.profile import FactStatus, LanguageCode, ProfileFact
from kisanpath.domain.profile_update import ProfileMerger
from kisanpath.domain.response import ResponseComposer, ResponseLocalizer
from kisanpath.persistence.repositories import ConversationRepository
from kisanpath.retrieval.models import (
    HybridRetrievalResult,
    RetrievalFilters,
    RetrievalQuery,
)
from kisanpath.workflows.exceptions import (
    ConversationNotFoundError,
    InvalidWorkflowTransitionError,
)
from kisanpath.workflows.models import (
    TextMessage,
    TextWorkflowResult,
    WorkflowEvent,
    WorkflowEventType,
)


class SchemeRetriever(Protocol):
    async def search(self, query: RetrievalQuery) -> tuple[HybridRetrievalResult, ...]: ...


_ALLOWED_TRANSITIONS: dict[WorkflowStage, set[WorkflowStage]] = {
    WorkflowStage.START: {WorkflowStage.PARSE_INPUT},
    WorkflowStage.END: {WorkflowStage.PARSE_INPUT},
    WorkflowStage.ASK_CLARIFICATION: {WorkflowStage.PARSE_INPUT},
    WorkflowStage.CONFIRM_VALUE: {WorkflowStage.PARSE_INPUT},
    WorkflowStage.PARSE_INPUT: {WorkflowStage.UPDATE_PROFILE},
    WorkflowStage.UPDATE_PROFILE: {
        WorkflowStage.CONFIRM_VALUE,
        WorkflowStage.DISCOVER_SCHEMES,
    },
    WorkflowStage.DISCOVER_SCHEMES: {WorkflowStage.EVALUATE_RULES},
    WorkflowStage.EVALUATE_RULES: {
        WorkflowStage.ASK_CLARIFICATION,
        WorkflowStage.VERIFY_EVIDENCE,
    },
    WorkflowStage.VERIFY_EVIDENCE: {WorkflowStage.COMPOSE_RESPONSE},
    WorkflowStage.COMPOSE_RESPONSE: {WorkflowStage.LOCALIZE},
    WorkflowStage.LOCALIZE: {WorkflowStage.END},
}


class TextEligibilityWorkflow:
    """Orchestrates typed state; raw chat replay is never required for correctness."""

    def __init__(
        self,
        *,
        conversations: ConversationRepository,
        profile_extractor: ProfileExtractor,
        profile_merger: ProfileMerger,
        retriever: SchemeRetriever,
        eligibility: EligibilityEngine,
        clarification: ClarificationPolicy | None = None,
        verifier: EvidenceVerifier | None = None,
        composer: ResponseComposer | None = None,
        localizer: ResponseLocalizer | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._conversations = conversations
        self._profile_extractor = profile_extractor
        self._profile_merger = profile_merger
        self._retriever = retriever
        self._eligibility = eligibility
        self._clarification = clarification or ClarificationPolicy()
        self._verifier = verifier or EvidenceVerifier()
        self._composer = composer or ResponseComposer()
        self._localizer = localizer or ResponseLocalizer()
        self._clock = clock or (lambda: datetime.now(UTC))

    async def create_conversation(
        self,
        conversation_id: str,
        *,
        preferred_language: LanguageCode = LanguageCode.ENGLISH,
    ) -> ConversationState:
        now = self._clock()
        state = ConversationState(
            conversation_id=conversation_id,
            preferred_language=preferred_language,
            created_at=now,
            updated_at=now,
        )
        await self._conversations.add_conversation(state)
        return state

    async def handle_text(self, conversation_id: str, message: TextMessage) -> TextWorkflowResult:
        state = await self._conversations.get_conversation(conversation_id)
        if state is None:
            raise ConversationNotFoundError(f"conversation not found: {conversation_id}")
        if message.message_id in state.processed_message_ids:
            return TextWorkflowResult(
                state=state,
                response_text=state.last_response_text or "Already processed.",
                events=(),
                idempotent_replay=True,
            )

        events: list[WorkflowEvent] = []
        pending_confirmation = state.pending_confirmation
        state = await self._transition(
            state,
            WorkflowStage.PARSE_INPUT,
            message_id=message.message_id,
            pending_confirmation=None,
            pending_clarification=None,
        )
        extraction = await self._profile_extractor.extract(
            ProfileExtractionRequest(
                message_id=message.message_id,
                text=message.text,
                preferred_language=message.language_hint or state.preferred_language,
                current_profile=state.current_profile,
                pending_confirmation=pending_confirmation,
            )
        )
        merge = self._profile_merger.merge(
            state.current_profile,
            extraction,
            message_id=message.message_id,
        )
        language = self._resolve_language(
            merge.profile.preferred_language,
            message.language_hint or state.preferred_language,
        )
        state = await self._transition(
            state,
            WorkflowStage.UPDATE_PROFILE,
            message_id=message.message_id,
            current_profile=merge.profile,
            preferred_language=language,
        )
        events.append(
            WorkflowEvent(
                event_type=WorkflowEventType.PROFILE_UPDATED,
                stage=state.workflow_stage,
                message="Canonical farmer profile updated.",
            )
        )

        if merge.confirmation_candidates:
            candidate = merge.confirmation_candidates[0]
            prompt = self._localizer.confirmation(
                candidate.field,
                candidate.proposed_value,
                language,
            )
            state = await self._transition(
                state,
                WorkflowStage.CONFIRM_VALUE,
                message_id=message.message_id,
                pending_confirmation=PendingConfirmation(
                    field=candidate.field,
                    proposed_value=candidate.proposed_value,
                    source_message_id=candidate.source_message_id,
                    prompt=prompt,
                ),
                processed_message_ids=(*state.processed_message_ids, message.message_id),
                last_response_text=prompt,
            )
            events.append(
                WorkflowEvent(
                    event_type=WorkflowEventType.CONFIRMATION_REQUIRED,
                    stage=state.workflow_stage,
                    message="A critical or conflicting profile value requires confirmation.",
                )
            )
            return TextWorkflowResult(state=state, response_text=prompt, events=tuple(events))

        state = await self._transition(
            state,
            WorkflowStage.DISCOVER_SCHEMES,
            message_id=message.message_id,
        )
        events.append(
            WorkflowEvent(
                event_type=WorkflowEventType.DISCOVERY_STARTED,
                stage=state.workflow_stage,
                message="Searching the reviewed published scheme corpus.",
            )
        )
        retrieval_results = await self._retriever.search(self._retrieval_query(state, message))
        candidate_ids = tuple(result.publication.scheme_id for result in retrieval_results)
        events.append(
            WorkflowEvent(
                event_type=WorkflowEventType.DISCOVERY_COMPLETED,
                stage=state.workflow_stage,
                message=f"Found {len(candidate_ids)} reviewed candidate schemes.",
            )
        )

        evaluations = tuple(
            await asyncio.gather(
                *(
                    self._eligibility.evaluate(
                        result.publication.scheme,
                        state.current_profile,
                    )
                    for result in retrieval_results
                )
            )
        )
        state = await self._transition(
            state,
            WorkflowStage.EVALUATE_RULES,
            message_id=message.message_id,
            candidate_scheme_ids=candidate_ids,
            latest_evaluations=evaluations,
        )
        events.append(
            WorkflowEvent(
                event_type=WorkflowEventType.ELIGIBILITY_COMPLETED,
                stage=state.workflow_stage,
                message="Reviewed eligibility rules evaluated.",
            )
        )

        clarification = self._clarification.choose(evaluations)
        if clarification is not None:
            prompt = self._localizer.clarification(clarification.field, language)
            state = await self._transition(
                state,
                WorkflowStage.ASK_CLARIFICATION,
                message_id=message.message_id,
                pending_clarification=PendingClarification(
                    field=clarification.field,
                    prompt=prompt,
                    affected_scheme_ids=clarification.affected_scheme_ids,
                    affected_rule_ids=clarification.affected_rule_ids,
                ),
                processed_message_ids=(*state.processed_message_ids, message.message_id),
                last_response_text=prompt,
            )
            events.append(
                WorkflowEvent(
                    event_type=WorkflowEventType.CLARIFICATION_REQUIRED,
                    stage=state.workflow_stage,
                    message="Missing information prevents a safe eligibility decision.",
                )
            )
            return TextWorkflowResult(state=state, response_text=prompt, events=tuple(events))

        schemes = tuple(result.publication.scheme for result in retrieval_results)
        verifications = self._verifier.verify(schemes, evaluations)
        state = await self._transition(
            state,
            WorkflowStage.VERIFY_EVIDENCE,
            message_id=message.message_id,
            latest_claim_verifications=verifications,
        )
        events.append(
            WorkflowEvent(
                event_type=WorkflowEventType.VERIFICATION_COMPLETED,
                stage=state.workflow_stage,
                message="Consequential claims checked against approved provenance.",
            )
        )
        plan = self._composer.compose(schemes, evaluations, verifications)
        state = await self._transition(
            state,
            WorkflowStage.COMPOSE_RESPONSE,
            message_id=message.message_id,
        )
        localized = self._localizer.localize(plan, language)
        state = await self._transition(
            state,
            WorkflowStage.LOCALIZE,
            message_id=message.message_id,
            last_response_text=localized.text,
        )
        state = await self._transition(
            state,
            WorkflowStage.END,
            message_id=message.message_id,
            processed_message_ids=(*state.processed_message_ids, message.message_id),
        )
        events.append(
            WorkflowEvent(
                event_type=WorkflowEventType.RESPONSE_READY,
                stage=state.workflow_stage,
                message="Localized evidence-backed response is ready.",
            )
        )
        return TextWorkflowResult(
            state=state,
            response_text=localized.text,
            events=tuple(events),
        )

    async def _transition(
        self,
        state: ConversationState,
        target: WorkflowStage,
        *,
        message_id: str,
        **updates: object,
    ) -> ConversationState:
        allowed = _ALLOWED_TRANSITIONS.get(state.workflow_stage, set())
        if target not in allowed:
            raise InvalidWorkflowTransitionError(
                f"cannot transition {state.workflow_stage.value} -> {target.value}"
            )
        now = self._clock()
        revision = state.revision + 1
        transition = WorkflowTransition(
            from_stage=state.workflow_stage,
            to_stage=target,
            occurred_at=now,
            revision=revision,
            trigger_message_id=message_id,
        )
        payload = state.model_dump(mode="python")
        payload.update(updates)
        payload.update(
            workflow_stage=target,
            updated_at=now,
            revision=revision,
            transitions=(*state.transitions, transition),
        )
        updated = ConversationState.model_validate(payload)
        await self._conversations.save_conversation(
            updated,
            expected_revision=state.revision,
        )
        return updated

    @staticmethod
    def _resolve_language(
        profile_fact: ProfileFact[LanguageCode], fallback: LanguageCode
    ) -> LanguageCode:
        if profile_fact.status is FactStatus.KNOWN and isinstance(profile_fact.value, LanguageCode):
            return profile_fact.value
        return fallback if fallback is not LanguageCode.UNDETERMINED else LanguageCode.ENGLISH

    @staticmethod
    def _retrieval_query(state: ConversationState, message: TextMessage) -> RetrievalQuery:
        profile = state.current_profile
        state_filter = profile.state.value if profile.state.status is FactStatus.KNOWN else None
        district_filter = (
            profile.district.value if profile.district.status is FactStatus.KNOWN else None
        )
        return RetrievalQuery(
            text=message.text,
            language=state.preferred_language.value,
            filters=RetrievalFilters(
                state=state_filter,
                district=district_filter,
            ),
        )
