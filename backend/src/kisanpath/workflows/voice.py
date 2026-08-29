"""Voice transport orchestration over the canonical text conversation workflow."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from kisanpath.domain.profile import InputModality, LanguageCode
from kisanpath.domain.profile_update import (
    ASRAmbiguityProvenance,
    ASRSegmentProvenance,
    ProfileMergeContext,
)
from kisanpath.voice.stt.base import STTClient
from kisanpath.voice.stt.models import AudioInput, TranscriptionRequest, TranscriptionResult
from kisanpath.voice.tts.base import TTSClient
from kisanpath.voice.tts.models import SynthesisRequest, SynthesisResult
from kisanpath.workflows.models import (
    TextMessage,
    TextWorkflowResult,
    WorkflowEvent,
    WorkflowEventType,
)
from kisanpath.workflows.text import TextEligibilityWorkflow


class VoiceMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    message_id: str = Field(min_length=1)
    audio: AudioInput
    language_hint: LanguageCode | None = None
    transcription_prompt: str | None = Field(default=None, min_length=1, max_length=1000)
    synthesize_response: bool = True


class VoiceWorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    transcript: TranscriptionResult
    conversation: TextWorkflowResult
    speech: SynthesisResult | None = None
    events: tuple[WorkflowEvent, ...] = ()


class VoiceEligibilityWorkflow:
    """Transcribes once, then delegates to the exact typed-message state machine."""

    def __init__(
        self,
        *,
        stt: STTClient,
        conversation: TextEligibilityWorkflow,
        tts: TTSClient | None = None,
    ) -> None:
        self._stt = stt
        self._conversation = conversation
        self._tts = tts

    async def handle_audio(
        self,
        conversation_id: str,
        message: VoiceMessage,
    ) -> VoiceWorkflowResult:
        transcript = await self._stt.transcribe(
            TranscriptionRequest(
                request_id=message.message_id,
                audio=message.audio,
                language_hint=message.language_hint,
                prompt=message.transcription_prompt,
            )
        )
        language = (
            transcript.language
            if transcript.language is not LanguageCode.UNDETERMINED
            else message.language_hint
        )
        context = ProfileMergeContext(
            source_message_id=message.message_id,
            source_modality=InputModality.VOICE,
            source_provider=transcript.provider,
            source_model=transcript.model,
            transcript_confidence=transcript.confidence,
            segments=tuple(
                ASRSegmentProvenance(
                    segment_id=item.segment_id,
                    text=item.text,
                    confidence=item.confidence,
                )
                for item in transcript.segments
            ),
            ambiguities=tuple(
                ASRAmbiguityProvenance(
                    ambiguity_id=item.ambiguity_id,
                    text=item.text,
                    alternatives=tuple(option.text for option in item.alternatives),
                )
                for item in transcript.ambiguities
            ),
        )
        conversation_result = await self._conversation.handle_text(
            conversation_id,
            TextMessage(
                message_id=message.message_id,
                text=transcript.text,
                language_hint=language,
            ),
            merge_context=context,
        )
        events = [
            WorkflowEvent(
                event_type=WorkflowEventType.TRANSCRIPT_READY,
                stage=conversation_result.state.workflow_stage,
                message="Voice input transcribed with provider provenance.",
            ),
            *conversation_result.events,
        ]
        speech = None
        if message.synthesize_response and self._tts is not None:
            speech = await self._tts.synthesize(
                SynthesisRequest(
                    request_id=f"{message.message_id}:response",
                    text=conversation_result.response_text,
                    language=conversation_result.state.preferred_language,
                )
            )
            events.append(
                WorkflowEvent(
                    event_type=WorkflowEventType.AUDIO_READY,
                    stage=conversation_result.state.workflow_stage,
                    message="Localized response audio is ready.",
                )
            )
        return VoiceWorkflowResult(
            transcript=transcript,
            conversation=conversation_result,
            speech=speech,
            events=tuple(events),
        )
