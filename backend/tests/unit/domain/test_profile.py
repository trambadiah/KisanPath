from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from kisanpath.domain.profile import (
    FactProvenance,
    FactStatus,
    FarmerProfile,
    LandNormalizationStatus,
    LandOwnership,
    LandUnit,
    ProfileFact,
    normalize_land_area,
)


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("2", LandUnit.HECTARE, Decimal("2.000000")),
        ("2", LandUnit.ACRE, Decimal("0.809371")),
        ("10000", LandUnit.SQUARE_METRE, Decimal("1.000000")),
    ],
)
def test_land_area_normalization_is_deterministic(
    value: str, unit: LandUnit, expected: Decimal
) -> None:
    result = normalize_land_area(value, unit)

    assert result.normalized_hectares == expected
    assert result.normalization_status is LandNormalizationStatus.NORMALIZED


def test_bigha_remains_unresolved_without_reviewed_regional_conversion() -> None:
    result = normalize_land_area("3", LandUnit.BIGHA)

    assert result.normalized_hectares is None
    assert result.normalization_status is LandNormalizationStatus.REGIONAL_CONTEXT_REQUIRED


def test_non_positive_land_area_is_rejected() -> None:
    with pytest.raises(ValidationError):
        normalize_land_area("0", LandUnit.HECTARE)


def test_unknown_fact_cannot_smuggle_a_value() -> None:
    with pytest.raises(ValidationError):
        ProfileFact[str](status=FactStatus.UNKNOWN, value="Gujarat")


def test_conflicting_fact_preserves_alternatives_without_selecting_one() -> None:
    fact = ProfileFact[LandOwnership](
        status=FactStatus.CONFLICTING,
        alternatives=(LandOwnership.OWNER, LandOwnership.TENANT),
    )

    assert fact.value is None
    assert fact.alternatives == (LandOwnership.OWNER, LandOwnership.TENANT)


def test_conflicting_fact_requires_distinct_alternatives() -> None:
    with pytest.raises(ValidationError):
        ProfileFact[str](status=FactStatus.CONFLICTING, alternatives=("owner", "owner"))


def test_profile_round_trip_preserves_provenance_and_decimal() -> None:
    profile = FarmerProfile(
        state=ProfileFact[str](
            status=FactStatus.KNOWN,
            value="Gujarat",
            provenance=(
                FactProvenance(source_message_id="message-1", confidence=0.98, confirmed=True),
            ),
        ),
        land_area=ProfileFact(
            status=FactStatus.KNOWN,
            value=normalize_land_area("2.5", LandUnit.ACRE),
        ),
    )

    serialized = profile.model_dump_json()
    restored = FarmerProfile.model_validate_json(serialized)

    assert restored == profile
    assert restored.land_area.value is not None
    assert restored.land_area.value.normalized_hectares == Decimal("1.011714")


def test_models_are_immutable() -> None:
    profile = FarmerProfile()
    with pytest.raises(ValidationError):
        profile.state = ProfileFact[str](status=FactStatus.KNOWN, value="Gujarat")
