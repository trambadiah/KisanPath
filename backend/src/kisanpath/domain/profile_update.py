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
    InputModality,
    IrrigationType,
    LandArea,
    LandNormalizationStatus,
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
    alternatives: tuple[JsonValue, ...] = ()
    source_modality: InputModality = InputModality.TEXT
    source_provider: str | None = Field(default=None, min_length=1)
    source_model: str | None = Field(default=None, min_length=1)
    asr_confidence: float | None = Field(default=None, ge=0, le=1)
    source_segment_ids: tuple[str, ...] = ()
    ambiguity_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_source(self) -> ConfirmationCandidate:
        if self.source_modality is InputModality.VOICE:
            if not self.source_provider or not self.source_model:
                raise ValueError("voice confirmation candidate requires provider and model")
        elif self.asr_confidence is not None or self.source_segment_ids or self.ambiguity_ids:
            raise ValueError("ASR metadata requires a voice confirmation candidate")
        return self


class ASRSegmentProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    segment_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=1000)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ASRAmbiguityProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ambiguity_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=500)
    alternatives: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_alternatives(self) -> ASRAmbiguityProvenance:
        normalized = tuple(item.casefold() for item in self.alternatives)
        if len(normalized) != len(set(normalized)):
            raise ValueError("ASR alternatives must be unique")
        return self


class FieldInputProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str | None = Field(default=None, min_length=1)
    source_message_id: str = Field(min_length=1)
    source_modality: InputModality
    source_provider: str | None = Field(default=None, min_length=1)
    source_model: str | None = Field(default=None, min_length=1)
    asr_confidence: float | None = Field(default=None, ge=0, le=1)
    source_segment_ids: tuple[str, ...] = ()
    ambiguity_ids: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_source(self) -> FieldInputProvenance:
        if self.source_modality is InputModality.VOICE:
            if not self.source_provider or not self.source_model:
                raise ValueError("voice field provenance requires provider and model")
        elif self.asr_confidence is not None or self.source_segment_ids or self.ambiguity_ids:
            raise ValueError("ASR metadata requires voice field provenance")
        if len(self.source_segment_ids) != len(set(self.source_segment_ids)):
            raise ValueError("source segment IDs must be unique")
        if len(self.ambiguity_ids) != len(set(self.ambiguity_ids)):
            raise ValueError("ambiguity IDs must be unique")
        return self


class ProfileMergeContext(BaseModel):
    """Trusted transport provenance supplied by text/voice orchestration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_message_id: str = Field(min_length=1)
    source_modality: InputModality = InputModality.TEXT
    source_provider: str | None = Field(default=None, min_length=1)
    source_model: str | None = Field(default=None, min_length=1)
    transcript_confidence: float | None = Field(default=None, ge=0, le=1)
    segments: tuple[ASRSegmentProvenance, ...] = ()
    ambiguities: tuple[ASRAmbiguityProvenance, ...] = ()
    field_sources: tuple[FieldInputProvenance, ...] = ()

    @model_validator(mode="after")
    def validate_context(self) -> ProfileMergeContext:
        if self.source_modality is InputModality.VOICE:
            if not self.source_provider or not self.source_model:
                raise ValueError("voice merge context requires provider and model")
        elif (
            self.transcript_confidence is not None
            or self.segments
            or self.ambiguities
            or any(item.source_modality is InputModality.VOICE for item in self.field_sources)
        ):
            raise ValueError("ASR metadata requires a voice merge context")
        explicit_fields = tuple(
            item.field for item in self.field_sources if item.field is not None
        )
        if len(explicit_fields) != len(set(explicit_fields)):
            raise ValueError("field sources must identify unique fields")
        segment_ids = tuple(item.segment_id for item in self.segments)
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("ASR segment IDs must be unique")
        ambiguity_ids = tuple(item.ambiguity_id for item in self.ambiguities)
        if len(ambiguity_ids) != len(set(ambiguity_ids)):
            raise ValueError("ASR ambiguity IDs must be unique")
        return self

    def for_field(self, field: str, utterance: str | None) -> FieldInputProvenance:
        explicit = next((item for item in self.field_sources if item.field == field), None)
        if explicit is not None:
            return explicit
        normalized = " ".join((utterance or "").casefold().split())
        matched_segments = tuple(
            segment
            for segment in self.segments
            if not normalized
            or normalized in " ".join(segment.text.casefold().split())
            or " ".join(segment.text.casefold().split()) in normalized
        )
        confidences = tuple(
            segment.confidence
            for segment in matched_segments
            if segment.confidence is not None
        )
        asr_confidence = min(confidences) if confidences else self.transcript_confidence
        matched_ambiguities = tuple(
            ambiguity
            for ambiguity in self.ambiguities
            if not normalized
            or " ".join(ambiguity.text.casefold().split()) in normalized
            or any(
                " ".join(alternative.casefold().split()) in normalized
                for alternative in ambiguity.alternatives
            )
        )
        return FieldInputProvenance(
            field=field,
            source_message_id=self.source_message_id,
            source_modality=self.source_modality,
            source_provider=self.source_provider,
            source_model=self.source_model,
            asr_confidence=asr_confidence,
            source_segment_ids=tuple(segment.segment_id for segment in matched_segments),
            ambiguity_ids=tuple(item.ambiguity_id for item in matched_ambiguities),
            alternatives=tuple(
                alternative
                for ambiguity in matched_ambiguities
                for alternative in ambiguity.alternatives
            ),
        )


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
        context: ProfileMergeContext | None = None,
    ) -> ProfileMergeResult:
        merge_context = context or ProfileMergeContext(source_message_id=message_id)
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
                    source=merge_context.for_field("state", extraction.state.source_utterance),
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
                    source=merge_context.for_field(
                        "district", extraction.district.source_utterance
                    ),
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
                    source=merge_context.for_field(
                        "village", extraction.village.source_utterance
                    ),
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
                    source=merge_context.for_field(
                        "land_area", extraction.land_area.source_utterance
                    ),
                    forced_confirmation_reason=(
                        "regional_land_unit_requires_confirmation"
                        if normalized_area.normalization_status
                        is LandNormalizationStatus.REGIONAL_CONTEXT_REQUIRED
                        and merge_context.source_modality is InputModality.VOICE
                        else None
                    ),
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
                        source=merge_context.for_field(name, extracted.source_utterance),
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
                        source=merge_context.for_field(name, extracted.source_utterance),
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
        source: FieldInputProvenance,
        forced_confirmation_reason: str | None = None,
    ) -> _FactMerge[ValueT]:
        confidences = tuple(
            confidence
            for confidence in (extracted.confidence, source.asr_confidence)
            if confidence is not None
        )
        effective_confidence = min(confidences) if confidences else None
        provenance = FactProvenance(
            source_message_id=source.source_message_id,
            source_utterance=extracted.source_utterance,
            confidence=effective_confidence,
            confirmed=confirmed,
            source_modality=source.source_modality,
            source_provider=source.source_provider,
            source_model=source.source_model,
            asr_confidence=source.asr_confidence,
            source_segment_ids=source.source_segment_ids,
            ambiguity_ids=source.ambiguity_ids,
            confirmed_by_message_id=message_id if confirmed else None,
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
        confirmation_reason = forced_confirmation_reason
        if source.ambiguity_ids:
            confirmation_reason = "asr_ambiguity_requires_confirmation"
        if (
            critical
            and not confirmed
            and (
                confirmation_reason is not None
                or effective_confidence is None
                or effective_confidence < self._critical_confidence_threshold
            )
        ):
            return _FactMerge(
                fact=current,
                changed=False,
                conflict=False,
                confirmation=ConfirmationCandidate(
                    field=field,
                    proposed_value=self._json_value(extracted.value),
                    source_message_id=source.source_message_id,
                    reason=confirmation_reason
                    or "critical_value_below_confidence_threshold",
                    alternatives=tuple(source.alternatives),
                    source_modality=source.source_modality,
                    source_provider=source.source_provider,
                    source_model=source.source_model,
                    asr_confidence=source.asr_confidence,
                    source_segment_ids=source.source_segment_ids,
                    ambiguity_ids=source.ambiguity_ids,
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
                source_message_id=source.source_message_id,
                reason="conflicts_with_canonical_profile",
                alternatives=tuple(source.alternatives),
                source_modality=source.source_modality,
                source_provider=source.source_provider,
                source_model=source.source_model,
                asr_confidence=source.asr_confidence,
                source_segment_ids=source.source_segment_ids,
                ambiguity_ids=source.ambiguity_ids,
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
