from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from kisanpath.domain.clarification import ClarificationPolicy
from kisanpath.domain.conversation import WorkflowStage
from kisanpath.domain.eligibility import RuleResult, RuleType, SchemeStatus
from kisanpath.domain.eligibility_engine import (
    EligibilityEngine,
    SemanticEvaluationRequest,
    SemanticRuleAssessment,
)
from kisanpath.domain.profile import LandUnit, LanguageCode
from kisanpath.domain.profile_update import (
    ExtractedLandArea,
    ExtractedValue,
    ProfileExtraction,
    ProfileMerger,
)
from kisanpath.domain.scheme import EligibilityRule, PublicationState, Scheme
from kisanpath.persistence.conversations import InMemoryConversationRepository
from kisanpath.persistence.models import PublishedSchemeVersion
from kisanpath.retrieval.models import (
    HybridRetrievalResult,
    RetrievalEvidence,
    RetrievalQuery,
)
from kisanpath.workflows.models import TextMessage, WorkflowEventType
from kisanpath.workflows.text import TextEligibilityWorkflow


class FixedProfileExtractor:
    def __init__(self, extraction: ProfileExtraction) -> None:
        self.extraction = extraction
        self.calls = 0

    async def extract(self, request: Any) -> ProfileExtraction:
        self.calls += 1
        return self.extraction


class FixedRetriever:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self.result = result
        self.queries: list[RetrievalQuery] = []

    async def search(self, query: RetrievalQuery) -> tuple[HybridRetrievalResult, ...]:
        self.queries.append(query)
        return (self.result,)


class AlwaysPassLLMSemanticEvaluator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def evaluate(self, request: SemanticEvaluationRequest) -> SemanticRuleAssessment:
        self.calls.append(request.rule.rule_id)
        return SemanticRuleAssessment(
            result=RuleResult.PASS,
            confidence=0.99,
            explanation="Mock LLM says the semantic condition passes.",
        )


def _published_result(synthetic_pipeline: Any) -> HybridRetrievalResult:
    scheme_payload = synthetic_pipeline.review.reviewed_scheme.model_dump(mode="python")
    scheme_payload["publication_state"] = PublicationState.PUBLISHED
    scheme = Scheme.model_validate(scheme_payload)
    publication = PublishedSchemeVersion(
        publication_id=synthetic_pipeline.publication.publication_id,
        scheme=scheme,
        human_review_id=synthetic_pipeline.review.review_id,
        published_by=synthetic_pipeline.publication.publisher.actor_id,
        published_at=synthetic_pipeline.publication.published_at,
    )
    chunk = synthetic_pipeline.parsed.chunks[1]
    return HybridRetrievalResult(
        publication=publication,
        structured_score=0.8,
        semantic_score=0.8,
        fused_score=0.8,
        structured_signals=("jurisdiction_state",),
        evidence=(
            RetrievalEvidence(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                source_ref_id=chunk.source_ref_id,
                locator=chunk.locator,
                bounded_excerpt=chunk.text,
            ),
        ),
    )


def _with_semantic_rule(result: HybridRetrievalResult) -> HybridRetrievalResult:
    payload = result.publication.scheme.model_dump(mode="python")
    semantic_rule = EligibilityRule(
        rule_id="synthetic-semantic-rule",
        scheme_id=result.publication.scheme_id,
        description="A fictional circumstance requires semantic interpretation.",
        rule_type=RuleType.SEMANTIC,
        source_ref_id="synthetic-source-001",
    ).model_dump(mode="python")
    payload["eligibility_rules"] = (*payload["eligibility_rules"], semantic_rule)
    publication_payload = result.publication.model_dump(mode="python")
    publication_payload["scheme"] = Scheme.model_validate(payload)
    publication = PublishedSchemeVersion.model_validate(publication_payload)
    result_payload = result.model_dump(mode="python")
    result_payload["publication"] = publication
    return HybridRetrievalResult.model_validate(result_payload)


@pytest.mark.asyncio
async def test_missing_information_causes_clarification_not_guessed_decision(
    synthetic_pipeline: Any,
) -> None:
    clock_time = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
    conversations = InMemoryConversationRepository()
    extractor = FixedProfileExtractor(
        ProfileExtraction(
            state=ExtractedValue(value="Gujarat", confidence=0.99),
            requested_needs=ExtractedValue(value=("micro-irrigation",), confidence=0.99),
        )
    )
    retriever = FixedRetriever(_published_result(synthetic_pipeline))
    workflow = TextEligibilityWorkflow(
        conversations=conversations,
        profile_extractor=extractor,
        profile_merger=ProfileMerger(),
        retriever=retriever,
        eligibility=EligibilityEngine(),
        clarification=ClarificationPolicy(),
        clock=lambda: clock_time,
    )
    await workflow.create_conversation("conversation-missing")

    result = await workflow.handle_text(
        "conversation-missing",
        TextMessage(
            message_id="message-missing",
            text="I am in Gujarat and need micro-irrigation support.",
        ),
    )

    assert result.state.workflow_stage is WorkflowStage.ASK_CLARIFICATION
    assert result.state.pending_clarification is not None
    assert result.state.pending_clarification.field == "land_area.normalized_hectares"
    assert result.state.latest_evaluations[0].status is SchemeStatus.INSUFFICIENT_INFORMATION
    assert "land area" in result.response_text.lower()
    assert WorkflowEventType.CLARIFICATION_REQUIRED in {event.event_type for event in result.events}
    persisted = await conversations.get_conversation("conversation-missing")
    assert persisted == result.state
    assert [transition.to_stage for transition in result.state.transitions] == [
        WorkflowStage.PARSE_INPUT,
        WorkflowStage.UPDATE_PROFILE,
        WorkflowStage.DISCOVER_SCHEMES,
        WorkflowStage.EVALUATE_RULES,
        WorkflowStage.ASK_CLARIFICATION,
    ]


@pytest.mark.asyncio
async def test_deterministic_fail_cannot_be_overridden_by_llm_component(
    synthetic_pipeline: Any,
) -> None:
    clock_time = datetime(2026, 8, 29, 11, 0, tzinfo=UTC)
    conversations = InMemoryConversationRepository()
    semantic = AlwaysPassLLMSemanticEvaluator()
    extractor = FixedProfileExtractor(
        ProfileExtraction(
            state=ExtractedValue(value="Gujarat", confidence=0.99),
            land_area=ExtractedValue(
                value=ExtractedLandArea(value=3, unit=LandUnit.HECTARE),
                confidence=0.99,
            ),
            requested_needs=ExtractedValue(value=("micro-irrigation",), confidence=0.99),
        )
    )
    retriever = FixedRetriever(_with_semantic_rule(_published_result(synthetic_pipeline)))
    workflow = TextEligibilityWorkflow(
        conversations=conversations,
        profile_extractor=extractor,
        profile_merger=ProfileMerger(),
        retriever=retriever,
        eligibility=EligibilityEngine(semantic_evaluator=semantic),
        clock=lambda: clock_time,
    )
    await workflow.create_conversation(
        "conversation-fail",
        preferred_language=LanguageCode.GUJARATI,
    )

    result = await workflow.handle_text(
        "conversation-fail",
        TextMessage(
            message_id="message-fail",
            text="મારી પાસે 3 હેક્ટર જમીન છે અને મને સિંચાઈ સહાય જોઈએ છે.",
            language_hint=LanguageCode.GUJARATI,
        ),
    )

    evaluation = result.state.latest_evaluations[0]
    assert semantic.calls == ["synthetic-semantic-rule"]
    assert evaluation.status is SchemeStatus.NOT_ELIGIBLE
    assert evaluation.blocking_rule_ids == ("synthetic-rule-001",)
    assert evaluation.rule_evaluations[1].result is RuleResult.PASS
    assert result.state.workflow_stage is WorkflowStage.END
    assert "પાત્ર નથી" in result.response_text
    assert result.state.latest_claim_verifications.publishable is True
    assert [transition.to_stage for transition in result.state.transitions] == [
        WorkflowStage.PARSE_INPUT,
        WorkflowStage.UPDATE_PROFILE,
        WorkflowStage.DISCOVER_SCHEMES,
        WorkflowStage.EVALUATE_RULES,
        WorkflowStage.VERIFY_EVIDENCE,
        WorkflowStage.COMPOSE_RESPONSE,
        WorkflowStage.LOCALIZE,
        WorkflowStage.END,
    ]

    replay = await workflow.handle_text(
        "conversation-fail",
        TextMessage(message_id="message-fail", text="duplicate request"),
    )
    assert replay.idempotent_replay is True
    assert replay.state.revision == result.state.revision
    assert extractor.calls == 1
