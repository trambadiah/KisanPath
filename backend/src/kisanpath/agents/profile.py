"""Provider-agnostic structured profile extraction agent."""

from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from kisanpath.domain.conversation import PendingConfirmation
from kisanpath.domain.profile import FarmerProfile, LanguageCode
from kisanpath.domain.profile_update import ProfileExtraction
from kisanpath.llm.base import LLMClient
from kisanpath.llm.models import (
    LLMMessage,
    LLMRequest,
    MessageRole,
    StructuredLLMRequest,
)


class ProfileExtractionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    message_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=8000)
    preferred_language: LanguageCode
    current_profile: FarmerProfile
    pending_confirmation: PendingConfirmation | None = None


class ProfileExtractor(Protocol):
    async def extract(self, request: ProfileExtractionRequest) -> ProfileExtraction: ...


class LLMProfileExtractor:
    """Uses local structured validation and never treats chat history as memory."""

    def __init__(
        self,
        client: LLMClient,
        *,
        prompt_version: str = "profile-extraction-v1",
    ) -> None:
        self._client = client
        self.prompt_version = prompt_version

    async def extract(self, request: ProfileExtractionRequest) -> ProfileExtraction:
        payload = {
            "message_id": request.message_id,
            "preferred_language": request.preferred_language.value,
            "current_profile": request.current_profile.model_dump(mode="json"),
            "pending_confirmation": (
                request.pending_confirmation.model_dump(mode="json")
                if request.pending_confirmation
                else None
            ),
            "latest_farmer_text": request.text,
        }
        llm_request = LLMRequest(
            messages=(
                LLMMessage(
                    role=MessageRole.SYSTEM,
                    content=(
                        "Extract only farmer facts explicitly supported by latest_farmer_text. "
                        "Use current_profile only to identify contradictions; never repeat or "
                        "invent missing values. Do not decide scheme eligibility. Preserve "
                        "ambiguity in ambiguity_notes and omit unsupported fields. If the "
                        "latest text explicitly confirms pending_confirmation, return that "
                        "value and list its field in confirmed_fields."
                    ),
                ),
                LLMMessage(
                    role=MessageRole.USER,
                    content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            ),
            temperature=0,
            max_output_tokens=1600,
            metadata={
                "agent": "profile_extractor",
                "prompt_version": self.prompt_version,
                "message_id": request.message_id,
            },
        )
        return await self._client.generate_structured(
            StructuredLLMRequest(
                request=llm_request,
                output_schema=ProfileExtraction,
                schema_name="kisanpath_profile_extraction_v1",
            )
        )
