"""Typed profile extraction output and deterministic merge policy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.types import JsonValue

from kisanpath.domain.profile import (
    FactProvenance,
    FactStatus,
    FarmerCategory,
    FarmerProfile,
    IrrigationType,
    LandArea,
    LandOwnership,
    LandUnit,
    LanguageCode,
    ProfileFact,
    normalize_land_area,
)

ValueT = TypeVar("ValueT")


class ExtractedValue(BaseModel, Generic[ValueT]):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: ValueT
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_utterance: str | None = Field(default=None, min_length=1, max_length=500)


class ExtractedLandArea(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    unit: LandUnit


class ProfileExtraction(BaseModel):
    """Only facts explicitly supported by the latest farmer message."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: ExtractedValue[str] | None = None
    district: ExtractedValue[str] | None = None
    village: ExtractedValue[str] | None = None
    land_area: ExtractedValue[ExtractedLandArea] | None = None
    land_ownership: ExtractedValue[LandOwnership] | None = None
    crops: ExtractedValue[tuple[str, ...]] | None = None
    irrigation_type: ExtractedValue[IrrigationType] | None = None
    farmer_category: ExtractedValue[FarmerCategory] | None = None
    requested_needs: ExtractedValue[tuple[str, ...]] | None = None
    preferred_language: ExtractedValue[LanguageCode] | None = None
    confirmed_fields: tuple[str, ...] = ()
    ambiguity_notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_unique_collections(self) -> ProfileExtraction:
        for name in ("crops", "requested_needs"):
            extracted = getattr(self, name)
            if extracted is not None:
                normalized = [item.casefold() for item in extracted.value]
                if not normalized or len(normalized) != len(set(normalized)):
                    raise ValueError(f"{name} must be non-empty and unique")
        if len(self.confirmed_fields) != len(set(self.confirmed_fields)):
            raise ValueError("confirmed fields must be unique")
        for field in self.confirmed_fields:
            if field not in type(self).model_fields or getattr(self, field, None) is None:
                raise ValueError("confirmed fields must reference an extracted value")
        return self


class ConfirmationCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(min_length=1)
    proposed_value: JsonValue
    source_message_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ProfileMergeResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile: FarmerProfile
    changed_fields: tuple[str, ...] = ()
    conflicting_fields: tuple[str, ...] = ()
    confirmation_candidates: tuple[ConfirmationCandidate, ...] = ()


@dataclass(frozen=True)
class _FactMerge(Generic[ValueT]):
    fact: ProfileFact[ValueT]
    changed: bool
    conflict: bool
    confirmation: ConfirmationCandidate | None


class ProfileMerger:
    """Merges explicit facts without silently replacing conflicts or low confidence."""

    def __init__(self, *, critical_confidence_threshold: float = 0.8) -> None:
        if not 0 <= critical_confidence_threshold <= 1:
            raise ValueError("critical confidence threshold must be between zero and one")
        self._critical_confidence_threshold = critical_confidence_threshold

    def merge(
        self,
        profile: FarmerProfile,
        extraction: ProfileExtraction,
        *,
        message_id: str,
    ) -> ProfileMergeResult:
        updates: dict[str, object] = {}
        changed: list[str] = []
        conflicts: list[str] = []
        confirmations: list[ConfirmationCandidate] = []

        def apply(name: str, result: _FactMerge[Any]) -> None:
            updates[name] = result.fact
            if result.changed:
                changed.append(name)
            if result.conflict:
                conflicts.append(name)
            if result.confirmation:
                confirmations.append(result.confirmation)

        if extraction.state:
            state = self._normalized_text(extraction.state, title=True)
            apply(
                "state",
                self._merge_fact(
                    profile.state,
                    state,
                    field="state",
                    message_id=message_id,
                    critical=True,
                    confirmed="state" in extraction.confirmed_fields,
                ),
            )
        if extraction.district:
            district = self._normalized_text(extraction.district, title=True)
            apply(
                "district",
                self._merge_fact(
                    profile.district,
                    district,
                    field="district",
                    message_id=message_id,
                    critical=True,
                    confirmed="district" in extraction.confirmed_fields,
                ),
            )
        if extraction.village:
            apply(
                "village",
                self._merge_fact(
                    profile.village,
                    self._normalized_text(extraction.village, title=True),
                    field="village",
                    message_id=message_id,
                    confirmed="village" in extraction.confirmed_fields,
                ),
            )
        if extraction.land_area:
            normalized_area = normalize_land_area(
                extraction.land_area.value.value,
                extraction.land_area.value.unit,
            )
            land_update = ExtractedValue[LandArea](
                value=normalized_area,
                confidence=extraction.land_area.confidence,
                source_utterance=extraction.land_area.source_utterance,
            )
            apply(
                "land_area",
                self._merge_fact(
                    profile.land_area,
                    land_update,
                    field="land_area",
                    message_id=message_id,
                    critical=True,
                    confirmed="land_area" in extraction.confirmed_fields,
                ),
            )

        def apply_scalar(
            name: str,
            current: ProfileFact[Any],
            extracted: ExtractedValue[Any] | None,
        ) -> None:
            if extracted:
                apply(
                    name,
                    self._merge_fact(
                        current,
                        extracted,
                        field=name,
                        message_id=message_id,
                        confirmed=name in extraction.confirmed_fields,
                    ),
                )

        apply_scalar("land_ownership", profile.land_ownership, extraction.land_ownership)
        apply_scalar("irrigation_type", profile.irrigation_type, extraction.irrigation_type)
        apply_scalar("farmer_category", profile.farmer_category, extraction.farmer_category)
        apply_scalar(
            "preferred_language", profile.preferred_language, extraction.preferred_language
        )

        def apply_tuple(
            name: str,
            current: ProfileFact[tuple[str, ...]],
            extracted: ExtractedValue[tuple[str, ...]] | None,
        ) -> None:
            if extracted:
                canonical = ExtractedValue[tuple[str, ...]](
                    value=tuple(dict.fromkeys(item.strip() for item in extracted.value)),
                    confidence=extracted.confidence,
                    source_utterance=extracted.source_utterance,
                )
                apply(
                    name,
                    self._merge_fact(
                        current,
                        canonical,
                        field=name,
                        message_id=message_id,
                        confirmed=name in extraction.confirmed_fields,
                    ),
                )

        apply_tuple("crops", profile.crops, extraction.crops)
        apply_tuple("requested_needs", profile.requested_needs, extraction.requested_needs)

        payload = profile.model_dump(mode="python")
        payload.update(updates)
        merged = FarmerProfile.model_validate(payload)
        return ProfileMergeResult(
            profile=merged,
            changed_fields=tuple(changed),
            conflicting_fields=tuple(conflicts),
            confirmation_candidates=tuple(confirmations),
        )

    def _merge_fact(
        self,
        current: ProfileFact[ValueT],
        extracted: ExtractedValue[ValueT],
        *,
        field: str,
        message_id: str,
        critical: bool = False,
        confirmed: bool = False,
    ) -> _FactMerge[ValueT]:
        provenance = FactProvenance(
            source_message_id=message_id,
            source_utterance=extracted.source_utterance,
            confidence=extracted.confidence,
            confirmed=confirmed,
        )
        if confirmed:
            return _FactMerge(
                fact=ProfileFact[ValueT](
                    status=FactStatus.KNOWN,
                    value=extracted.value,
                    provenance=(*current.provenance, provenance),
                ),
                changed=(
                    current.status is not FactStatus.KNOWN or current.value != extracted.value
                ),
                conflict=False,
                confirmation=None,
            )
        if (
            critical
            and not confirmed
            and (
                extracted.confidence is None
                or extracted.confidence < self._critical_confidence_threshold
            )
        ):
            return _FactMerge(
                fact=current,
                changed=False,
                conflict=False,
                confirmation=ConfirmationCandidate(
                    field=field,
                    proposed_value=self._json_value(extracted.value),
                    source_message_id=message_id,
                    reason="critical_value_below_confidence_threshold",
                ),
            )
        if current.status is FactStatus.UNKNOWN:
            return _FactMerge(
                fact=ProfileFact[ValueT](
                    status=FactStatus.KNOWN,
                    value=extracted.value,
                    provenance=(provenance,),
                ),
                changed=True,
                conflict=False,
                confirmation=None,
            )
        if current.status is FactStatus.KNOWN and current.value == extracted.value:
            return _FactMerge(
                fact=ProfileFact[ValueT](
                    status=FactStatus.KNOWN,
                    value=current.value,
                    provenance=(*current.provenance, provenance),
                ),
                changed=False,
                conflict=False,
                confirmation=None,
            )
        alternatives: tuple[ValueT, ...]
        if current.status is FactStatus.KNOWN:
            assert current.value is not None
            alternatives = (current.value, extracted.value)
        else:
            alternatives = (*current.alternatives, extracted.value)
        unique = tuple(dict.fromkeys(alternatives))
        return _FactMerge(
            fact=ProfileFact[ValueT](
                status=FactStatus.CONFLICTING,
                alternatives=unique,
                provenance=(*current.provenance, provenance),
            ),
            changed=True,
            conflict=True,
            confirmation=ConfirmationCandidate(
                field=field,
                proposed_value=self._json_value(extracted.value),
                source_message_id=message_id,
                reason="conflicts_with_canonical_profile",
            ),
        )

    @staticmethod
    def _normalized_text(extracted: ExtractedValue[str], *, title: bool) -> ExtractedValue[str]:
        value = " ".join(extracted.value.split())
        if title:
            value = value.title()
        return ExtractedValue[str](
            value=value,
            confidence=extracted.confidence,
            source_utterance=extracted.source_utterance,
        )

    @staticmethod
    def _json_value(value: object) -> JsonValue:
        if isinstance(value, BaseModel):
            return json.loads(value.model_dump_json())  # type: ignore[no-any-return]
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, Decimal):
            return str(value)
        return value  # type: ignore[return-value]
