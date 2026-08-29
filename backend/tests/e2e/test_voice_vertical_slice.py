from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from kisanpath.domain.conversation import WorkflowStage
from kisanpath.domain.eligibility_engine import EligibilityEngine
from kisanpath.domain.profile import FactStatus, InputModality, LandUnit, LanguageCode
from kisanpath.domain.profile_update import (
    ExtractedLandArea,
    ExtractedValue,
    ProfileExtraction,
    ProfileMerger,
)
from kisanpath.persistence.conversations import InMemoryConversationRepository
from kisanpath.voice.stt.models import (
    AudioInput,
    AudioMediaType,
    STTCapabilities,
    STTHealth,
    TranscriptAlternative,
    TranscriptAmbiguity,
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptSegment,
)
from kisanpath.voice.tts.models import (
    SpeechAudioFormat,
    SynthesisRequest,
    SynthesisResult,
    TTSCapabilities,
    TTSHealth,
)
from kisanpath.workflows.models import TextMessage, WorkflowEventType
from kisanpath.workflows.text import TextEligibilityWorkflow
from kisanpath.workflows.voice import VoiceEligibilityWorkflow, VoiceMessage


class SequencedExtractor:
    def __init__(self, extractions: tuple[ProfileExtraction, ...]) -> None:
        self.extractions = iter(extractions)

    async def extract(self, request: Any) -> ProfileExtraction:
        return next(self.extractions)


class EmptyRetriever:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, query: Any) -> tuple[Any, ...]:
        self.calls += 1
        return ()


class SimulatedAmbiguousSTT:
    provider = "simulated-stt"
    model = "synthetic-asr-v1"
    capabilities = STTCapabilities(
        confidence=True,
        segment_timestamps=True,
        alternatives=True,
        language_hints=True,
    )

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        return TranscriptionResult(
            transcript_id=request.request_id,
            text="મારી પાસે 3 એકર જમીન છે",
            language=LanguageCode.GUJARATI,
            confidence=0.91,
            segments=(
                TranscriptSegment(
                    segment_id="land-segment",
                    text="મારી પાસે 3 એકર જમીન છે",
                    confidence=0.91,
                ),
            ),
            ambiguities=(
                TranscriptAmbiguity(
                    ambiguity_id="three-or-thirty",
                    text="3 એકર",
                    segment_ids=("land-segment",),
                    alternatives=(
                        TranscriptAlternative(text="3 એકર", confidence=0.55),
                        TranscriptAlternative(text="30 એકર", confidence=0.45),
                    ),
                ),
            ),
            provider=self.provider,
            model=self.model,
        )

    async def healthcheck(self) -> STTHealth:
        return STTHealth(available=True, provider=self.provider, model=self.model)


class SimulatedTTS:
    provider = "simulated-tts"
    model = "synthetic-tts-v1"
    capabilities = TTSCapabilities(
        audio_formats=frozenset({SpeechAudioFormat.MP3}),
        configurable_voice=False,
        configurable_speed=False,
        instructions=False,
    )

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        return SynthesisResult(
            request_id=request.request_id,
            audio=b"synthetic-response-audio",
            media_type="audio/mpeg",
            audio_format=SpeechAudioFormat.MP3,
            provider=self.provider,
            model=self.model,
            voice="synthetic",
        )

    async def healthcheck(self) -> TTSHealth:
        return TTSHealth(available=True, provider=self.provider, model=self.model)


@pytest.mark.asyncio
async def test_voice_uses_canonical_workflow_and_confirmation_preserves_asr_source() -> None:
    land = ExtractedValue(
        value=ExtractedLandArea(value=Decimal("3"), unit=LandUnit.ACRE),
        confidence=0.99,
        source_utterance="3 એકર",
    )
    conversations = InMemoryConversationRepository()
    retriever = EmptyRetriever()
    text = TextEligibilityWorkflow(
        conversations=conversations,
        profile_extractor=SequencedExtractor(
            (
                ProfileExtraction(land_area=land),
                ProfileExtraction(land_area=land, confirmed_fields=("land_area",)),
            )
        ),
        profile_merger=ProfileMerger(),
        retriever=retriever,
        eligibility=EligibilityEngine(),
    )
    await text.create_conversation("voice-conversation")
    voice = VoiceEligibilityWorkflow(
        stt=SimulatedAmbiguousSTT(), conversation=text, tts=SimulatedTTS()
    )

    first = await voice.handle_audio(
        "voice-conversation",
        VoiceMessage(
            message_id="voice-message",
            audio=AudioInput(
                content=b"synthetic-audio",
                filename="synthetic.wav",
                media_type=AudioMediaType.WAV,
            ),
        ),
    )

    assert first.conversation.state.workflow_stage is WorkflowStage.CONFIRM_VALUE
    assert first.conversation.state.current_profile.land_area.status is FactStatus.UNKNOWN
    pending = first.conversation.state.pending_confirmation
    assert pending is not None
    assert pending.reason == "asr_ambiguity_requires_confirmation"
    assert pending.alternatives == ("3 એકર", "30 એકર")
    assert pending.source_modality is InputModality.VOICE
    assert pending.source_provider == "simulated-stt"
    assert pending.asr_confidence == 0.91
    assert first.speech is not None
    assert retriever.calls == 0
    assert WorkflowEventType.TRANSCRIPT_READY in {event.event_type for event in first.events}
    assert WorkflowEventType.AUDIO_READY in {event.event_type for event in first.events}

    confirmed = await text.handle_text(
        "voice-conversation",
        TextMessage(message_id="confirmation-message", text="Yes, 3 acres."),
    )

    fact = confirmed.state.current_profile.land_area
    assert fact.status is FactStatus.KNOWN
    provenance = fact.provenance[-1]
    assert provenance.source_message_id == "voice-message"
    assert provenance.confirmed_by_message_id == "confirmation-message"
    assert provenance.source_modality is InputModality.VOICE
    assert provenance.source_provider == "simulated-stt"
    assert provenance.ambiguity_ids == ("three-or-thirty",)
    assert retriever.calls == 1
