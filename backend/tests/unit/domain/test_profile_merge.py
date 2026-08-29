from __future__ import annotations

from kisanpath.domain.profile import (
    FactProvenance,
    FactStatus,
    FarmerProfile,
    ProfileFact,
)
from kisanpath.domain.profile_update import ExtractedValue, ProfileExtraction, ProfileMerger


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
