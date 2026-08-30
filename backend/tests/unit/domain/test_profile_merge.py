from __future__ import annotations

from decimal import Decimal

from kisanpath.domain.profile import (
    FactProvenance,
    FactStatus,
    FarmerProfile,
    InputModality,
    LandUnit,
    ProfileFact,
)
from kisanpath.domain.profile_update import (
    ASRAmbiguityProvenance,
    ASRSegmentProvenance,
    ExtractedLandArea,
    ExtractedValue,
    FieldInputProvenance,
    ProfileExtraction,
    ProfileMergeContext,
    ProfileMerger,
)


def test_merge_adds_explicit_fact_with_message_provenance() -> None:
    result = ProfileMerger().merge(
        FarmerProfile(),
        ProfileExtraction(
            state=ExtractedValue(value="  gujarat ", confidence=0.99),
        ),
        message_id="message-1",
    )

    assert result.profile.state.value == "Gujarat"
    assert result.profile.state.provenance[0].source_message_id == "message-1"
    assert result.changed_fields == ("state",)


def test_conflicting_fact_is_preserved_and_requires_confirmation() -> None:
    profile = FarmerProfile(
        state=ProfileFact[str](
            status=FactStatus.KNOWN,
            value="Gujarat",
            provenance=(FactProvenance(source_message_id="message-old", confirmed=True),),
        )
    )
    result = ProfileMerger().merge(
        profile,
        ProfileExtraction(state=ExtractedValue(value="Rajasthan", confidence=0.99)),
        message_id="message-new",
    )

    assert result.profile.state.status is FactStatus.CONFLICTING
    assert result.profile.state.alternatives == ("Gujarat", "Rajasthan")
    assert result.conflicting_fields == ("state",)
    assert result.confirmation_candidates[0].reason == "conflicts_with_canonical_profile"


def test_low_confidence_critical_fact_is_not_merged() -> None:
    result = ProfileMerger(critical_confidence_threshold=0.8).merge(
        FarmerProfile(),
        ProfileExtraction(state=ExtractedValue(value="Gujarat", confidence=0.4)),
        message_id="message-low-confidence",
    )

    assert result.profile.state.status is FactStatus.UNKNOWN
    assert result.changed_fields == ()
    assert result.confirmation_candidates[0].field == "state"


def test_explicitly_confirmed_critical_fact_bypasses_confidence_prompt() -> None:
    result = ProfileMerger(critical_confidence_threshold=0.8).merge(
        FarmerProfile(),
        ProfileExtraction(
            state=ExtractedValue(value="Gujarat", confidence=0.4),
            confirmed_fields=("state",),
        ),
        message_id="message-confirmed",
    )

    assert result.profile.state.value == "Gujarat"
    assert result.profile.state.provenance[0].confirmed is True
    assert result.confirmation_candidates == ()


def test_explicit_confirmation_resolves_a_previous_conflict() -> None:
    conflicting = ProfileFact[str](
        status=FactStatus.CONFLICTING,
        alternatives=("Gujarat", "Rajasthan"),
        provenance=(FactProvenance(source_message_id="message-conflict"),),
    )
    result = ProfileMerger().merge(
        FarmerProfile(state=conflicting),
        ProfileExtraction(
            state=ExtractedValue(value="Rajasthan", confidence=0.99),
            confirmed_fields=("state",),
        ),
        message_id="message-confirmation",
    )

    assert result.profile.state.status is FactStatus.KNOWN
    assert result.profile.state.value == "Rajasthan"
    assert result.profile.state.provenance[-1].confirmed is True
    assert result.conflicting_fields == ()


def test_asr_three_vs_thirty_acres_requires_confirmation_and_preserves_provenance() -> None:
    context = ProfileMergeContext(
        source_message_id="voice-message-1",
        source_modality=InputModality.VOICE,
        source_provider="mock-stt",
        source_model="mock-asr-v1",
        transcript_confidence=0.91,
        segments=(
            ASRSegmentProvenance(
                segment_id="segment-land",
                text="I have 3 acres of land",
                confidence=0.91,
            ),
        ),
        ambiguities=(
            ASRAmbiguityProvenance(
                ambiguity_id="ambiguity-number",
                text="3 acres",
                alternatives=("3 acres", "30 acres"),
            ),
        ),
    )
    extraction = ProfileExtraction(
        land_area=ExtractedValue(
            value=ExtractedLandArea(value=Decimal("3"), unit=LandUnit.ACRE),
            confidence=0.99,
            source_utterance="3 acres",
        )
    )

    result = ProfileMerger().merge(
        FarmerProfile(), extraction, message_id="voice-message-1", context=context
    )

    assert result.profile.land_area.status is FactStatus.UNKNOWN
    candidate = result.confirmation_candidates[0]
    assert candidate.reason == "asr_ambiguity_requires_confirmation"
    assert candidate.alternatives == ("3 acres", "30 acres")
    assert candidate.asr_confidence == 0.91
    assert candidate.source_segment_ids == ("segment-land",)
    assert candidate.ambiguity_ids == ("ambiguity-number",)

    confirmed_context = ProfileMergeContext(
        source_message_id="confirmation-message",
        source_modality=InputModality.VOICE,
        source_provider="mock-stt",
        source_model="mock-asr-v1",
        transcript_confidence=0.91,
        field_sources=(
            FieldInputProvenance(
                field="land_area",
                source_message_id="voice-message-1",
                source_modality=InputModality.VOICE,
                source_provider="mock-stt",
                source_model="mock-asr-v1",
                asr_confidence=0.91,
                source_segment_ids=("segment-land",),
                ambiguity_ids=("ambiguity-number",),
                alternatives=("3 acres", "30 acres"),
            ),
        ),
    )
    confirmed = ProfileMerger().merge(
        FarmerProfile(),
        extraction.model_copy(update={"confirmed_fields": ("land_area",)}),
        message_id="confirmation-message",
        context=confirmed_context,
    )

    provenance = confirmed.profile.land_area.provenance[0]
    assert provenance.source_message_id == "voice-message-1"
    assert provenance.confirmed_by_message_id == "confirmation-message"
    assert provenance.source_modality is InputModality.VOICE
    assert provenance.asr_confidence == 0.91
    assert provenance.ambiguity_ids == ("ambiguity-number",)


def test_ambiguous_regional_land_unit_from_voice_requires_confirmation() -> None:
    context = ProfileMergeContext(
        source_message_id="voice-message-bigha",
        source_modality=InputModality.VOICE,
        source_provider="mock-stt",
        source_model="mock-asr-v1",
        transcript_confidence=0.98,
        segments=(
            ASRSegmentProvenance(
                segment_id="segment-bigha",
                text="I cultivate 2 bigha",
                confidence=0.98,
            ),
        ),
    )
    result = ProfileMerger().merge(
        FarmerProfile(),
        ProfileExtraction(
            land_area=ExtractedValue(
                value=ExtractedLandArea(value=2, unit=LandUnit.BIGHA),
                confidence=0.99,
                source_utterance="2 bigha",
            )
        ),
        message_id="voice-message-bigha",
        context=context,
    )

    assert result.profile.land_area.status is FactStatus.UNKNOWN
    assert result.confirmation_candidates[0].reason == "regional_land_unit_requires_confirmation"
