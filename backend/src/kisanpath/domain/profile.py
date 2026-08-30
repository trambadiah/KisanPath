"""Canonical farmer profile facts and deterministic land normalization."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LanguageCode(StrEnum):
    GUJARATI = "gu"
    HINDI = "hi"
    ENGLISH = "en"
    UNDETERMINED = "und"


class InputModality(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class FactStatus(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    CONFLICTING = "conflicting"


class LandUnit(StrEnum):
    HECTARE = "hectare"
    ACRE = "acre"
    SQUARE_METRE = "square_metre"
    BIGHA = "bigha"


class LandNormalizationStatus(StrEnum):
    NORMALIZED = "normalized"
    REGIONAL_CONTEXT_REQUIRED = "regional_context_required"


class LandOwnership(StrEnum):
    OWNER = "owner"
    TENANT = "tenant"
    SHARECROPPER = "sharecropper"
    OTHER = "other"
    UNKNOWN = "unknown"


class IrrigationType(StrEnum):
    RAINFED = "rainfed"
    CANAL = "canal"
    WELL = "well"
    BOREWELL = "borewell"
    DRIP = "drip"
    SPRINKLER = "sprinkler"
    OTHER = "other"
    UNKNOWN = "unknown"


class FarmerCategory(StrEnum):
    MARGINAL = "marginal"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    UNKNOWN = "unknown"


class FactProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_message_id: str = Field(min_length=1)
    source_utterance: str | None = Field(default=None, min_length=1, max_length=500)
    confidence: float | None = Field(default=None, ge=0, le=1)
    confirmed: bool = False
    source_modality: InputModality = InputModality.TEXT
    source_provider: str | None = Field(default=None, min_length=1)
    source_model: str | None = Field(default=None, min_length=1)
    asr_confidence: float | None = Field(default=None, ge=0, le=1)
    source_segment_ids: tuple[str, ...] = ()
    ambiguity_ids: tuple[str, ...] = ()
    confirmed_by_message_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_source(self) -> FactProvenance:
        if self.source_modality is InputModality.VOICE:
            if not self.source_provider or not self.source_model:
                raise ValueError("voice provenance requires provider and model")
        elif self.asr_confidence is not None or self.source_segment_ids or self.ambiguity_ids:
            raise ValueError("ASR metadata is only valid for voice provenance")
        if len(self.source_segment_ids) != len(set(self.source_segment_ids)):
            raise ValueError("source segment IDs must be unique")
        if len(self.ambiguity_ids) != len(set(self.ambiguity_ids)):
            raise ValueError("ambiguity IDs must be unique")
        if self.confirmed_by_message_id and not self.confirmed:
            raise ValueError("confirmed_by_message_id requires confirmed provenance")
        return self


FactT = TypeVar("FactT")


class ProfileFact(BaseModel, Generic[FactT]):
    """A profile value that never collapses unknowns or contradictions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: FactStatus
    value: FactT | None = None
    alternatives: tuple[FactT, ...] = ()
    provenance: tuple[FactProvenance, ...] = ()

    @model_validator(mode="after")
    def validate_state(self) -> ProfileFact[FactT]:
        if self.status is FactStatus.KNOWN:
            if self.value is None:
                raise ValueError("known facts require a value")
            if self.alternatives:
                raise ValueError("known facts cannot contain alternatives")
        elif self.status is FactStatus.UNKNOWN:
            if self.value is not None or self.alternatives:
                raise ValueError("unknown facts cannot contain values or alternatives")
        else:
            if self.value is not None:
                raise ValueError("conflicting facts cannot select a canonical value")
            if len(self.alternatives) < 2:
                raise ValueError("conflicting facts require at least two alternatives")
            if len(set(map(repr, self.alternatives))) != len(self.alternatives):
                raise ValueError("conflicting alternatives must be unique")
        return self

    @classmethod
    def unknown(cls) -> ProfileFact[FactT]:
        return cls(status=FactStatus.UNKNOWN)


class LandArea(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    unit: LandUnit
    normalized_hectares: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=6)
    normalization_status: LandNormalizationStatus
    normalization_rule: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_normalization(self) -> LandArea:
        if self.normalization_status is LandNormalizationStatus.NORMALIZED:
            if self.normalized_hectares is None or not self.normalization_rule:
                raise ValueError("normalized land area requires a value and normalization rule")
        elif self.normalized_hectares is not None:
            raise ValueError("ambiguous land units cannot have normalized hectares")
        return self


_HECTARES_PER_UNIT = {
    LandUnit.HECTARE: Decimal("1"),
    LandUnit.ACRE: Decimal("0.40468564224"),
    LandUnit.SQUARE_METRE: Decimal("0.0001"),
}
_HECTARE_QUANTUM = Decimal("0.000001")


def normalize_land_area(value: Decimal | int | str, unit: LandUnit) -> LandArea:
    """Normalize stable SI/acre units; preserve regional `bigha` as unresolved."""

    decimal_value = Decimal(str(value))
    if unit is LandUnit.BIGHA:
        return LandArea(
            value=decimal_value,
            unit=unit,
            normalization_status=LandNormalizationStatus.REGIONAL_CONTEXT_REQUIRED,
            normalization_rule="bigha_requires_reviewed_regional_conversion",
        )
    factor = _HECTARES_PER_UNIT[unit]
    normalized = (decimal_value * factor).quantize(_HECTARE_QUANTUM, rounding=ROUND_HALF_UP)
    return LandArea(
        value=decimal_value,
        unit=unit,
        normalized_hectares=normalized,
        normalization_status=LandNormalizationStatus.NORMALIZED,
        normalization_rule=f"{unit.value}_to_hectare_v1",
    )


class FarmerProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: ProfileFact[str] = Field(default_factory=ProfileFact[str].unknown)
    district: ProfileFact[str] = Field(default_factory=ProfileFact[str].unknown)
    village: ProfileFact[str] = Field(default_factory=ProfileFact[str].unknown)
    land_area: ProfileFact[LandArea] = Field(default_factory=ProfileFact[LandArea].unknown)
    land_ownership: ProfileFact[LandOwnership] = Field(
        default_factory=ProfileFact[LandOwnership].unknown
    )
    crops: ProfileFact[tuple[str, ...]] = Field(
        default_factory=ProfileFact[tuple[str, ...]].unknown
    )
    irrigation_type: ProfileFact[IrrigationType] = Field(
        default_factory=ProfileFact[IrrigationType].unknown
    )
    farmer_category: ProfileFact[FarmerCategory] = Field(
        default_factory=ProfileFact[FarmerCategory].unknown
    )
    requested_needs: ProfileFact[tuple[str, ...]] = Field(
        default_factory=ProfileFact[tuple[str, ...]].unknown
    )
    preferred_language: ProfileFact[LanguageCode] = Field(
        default_factory=ProfileFact[LanguageCode].unknown
    )
