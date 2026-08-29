"""LLM-backed evaluator limited to rules explicitly typed as semantic."""

from __future__ import annotations

import json

from kisanpath.domain.eligibility_engine import (
    SemanticEvaluationRequest,
    SemanticRuleAssessment,
)
from kisanpath.llm.base import LLMClient
from kisanpath.llm.models import (
    LLMMessage,
    LLMRequest,
    MessageRole,
    StructuredLLMRequest,
)


class LLMSemanticRuleEvaluator:
    def __init__(
        self,
        client: LLMClient,
        *,
        prompt_version: str = "semantic-eligibility-v1",
    ) -> None:
        self._client = client
        self.prompt_version = prompt_version

    async def evaluate(self, request: SemanticEvaluationRequest) -> SemanticRuleAssessment:
        payload = {
            "rule": request.rule.model_dump(mode="json"),
            "farmer_profile": request.profile.model_dump(mode="json"),
            "approved_source_excerpt": request.approved_source_excerpt,
        }
        llm_request = LLMRequest(
            messages=(
                LLMMessage(
                    role=MessageRole.SYSTEM,
                    content=(
                        "Evaluate only the supplied semantic eligibility rule against explicit "
                        "profile facts and approved evidence. Unknown facts remain UNKNOWN. "
                        "Do not evaluate deterministic rules and do not infer missing facts."
                    ),
                ),
                LLMMessage(
                    role=MessageRole.USER,
                    content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            ),
            temperature=0,
            max_output_tokens=700,
            metadata={
                "agent": "semantic_eligibility",
                "prompt_version": self.prompt_version,
                "rule_id": request.rule.rule_id,
            },
        )
        return await self._client.generate_structured(
            StructuredLLMRequest(
                request=llm_request,
                output_schema=SemanticRuleAssessment,
                schema_name="kisanpath_semantic_rule_assessment_v1",
            )
        )
