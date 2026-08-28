from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from kisanpath.domain.eligibility import EligibilityOperator, RuleType
from kisanpath.domain.scheme import (
    EligibilityRule,
    Jurisdiction,
    PublicationState,
    Scheme,
    SchemeVersion,
    SourcedText,
    SourceReference,
    SourceReviewStatus,
)
from kisanpath.ingestion.models import (
    ActorKind,
    ExtractedSchemeCandidate,
    ExtractionMethod,
    HumanReviewApproval,
    ParsedDocument,
    PublicationApproval,
    TransitionActor,
    ValidatedSchemeCandidate,
)
from kisanpath.persistence.models import ParsedDocumentChunk, SourceDocumentRecord

FIXED_TIME = datetime(2026, 8, 28, 10, 0, tzinfo=UTC)


@dataclass(frozen=True)
class SyntheticPipelineFixture:
    source: SourceDocumentRecord
    parsed: ParsedDocument
    extracted: ExtractedSchemeCandidate
    validated: ValidatedSchemeCandidate
    review: HumanReviewApproval
    publication: PublicationApproval
    system_actor: TransitionActor


def _load_document_fixture() -> dict[str, Any]:
    fixture_path = Path(__file__).parent / "fixtures" / "synthetic_scheme_document.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _reviewed_copy(draft: Scheme) -> Scheme:
    payload = draft.model_dump(mode="python")
    payload["publication_state"] = PublicationState.IN_REVIEW
    payload["official_sources"] = [
        {**source, "review_status": SourceReviewStatus.APPROVED}
        for source in payload["official_sources"]
    ]
    return Scheme.model_validate(payload)


@pytest.fixture
def synthetic_pipeline() -> SyntheticPipelineFixture:
    fixture = _load_document_fixture()
    raw_content = str(fixture["raw_content"])
    document_id = str(fixture["document_id"])
    source = SourceDocumentRecord(
        document_id=document_id,
        title=str(fixture["title"]),
        media_type=str(fixture["media_type"]),
        origin_locator=str(fixture["origin_locator"]),
        snapshot_locator=str(fixture["snapshot_locator"]),
        content_sha256=hashlib.sha256(raw_content.encode()).hexdigest(),
        imported_at=FIXED_TIME,
        imported_by="synthetic-fixture-loader",
        synthetic=True,
    )
    chunks = tuple(
        ParsedDocumentChunk(document_id=document_id, **chunk) for chunk in fixture["chunks"]
    )
    parsed = ParsedDocument(
        document_id=document_id,
        parser_version="synthetic-parser-v1",
        parsed_at=FIXED_TIME + timedelta(minutes=1),
        chunks=chunks,
    )
    source_references = tuple(
        SourceReference(
            source_id=chunk.source_ref_id,
            document_id=document_id,
            source_locator=source.snapshot_locator,
            title=source.title,
            locator=chunk.locator,
            imported_at=source.imported_at,
            review_status=SourceReviewStatus.PENDING,
            bounded_excerpt=chunk.text,
        )
        for chunk in chunks
    )
    summary = SourcedText(
        text="Fictional Gujarat micro-irrigation support.",
        source_ref_ids=("synthetic-source-001",),
    )
    benefit = SourcedText(
        text="Mock equipment voucher.",
        source_ref_ids=("synthetic-source-003",),
    )
    scheme = Scheme(
        scheme_id="synthetic-scheme-001",
        name="Synthetic Micro-Irrigation Support",
        authority="Synthetic Test Authority",
        jurisdiction=Jurisdiction(states=("Gujarat",)),
        categories=("micro-irrigation",),
        summary=summary,
        benefits=(benefit,),
        eligibility_rules=(
            EligibilityRule(
                rule_id="synthetic-rule-001",
                scheme_id="synthetic-scheme-001",
                description="Reported land area must not exceed two hectares.",
                rule_type=RuleType.DETERMINISTIC,
                field="land_area.normalized_hectares",
                operator=EligibilityOperator.LTE,
                expected_value=2,
                normalization_rule="convert_supported_land_unit_to_hectares",
                source_ref_id="synthetic-source-002",
            ),
        ),
        required_documents=(),
        application_steps=(),
        official_sources=source_references,
        publication_state=PublicationState.DRAFT,
        version=SchemeVersion(
            version_id="synthetic-version-001",
            effective_from=date(2026, 1, 1),
            corpus_version="synthetic-corpus-v1",
        ),
    )
    extracted = ExtractedSchemeCandidate(
        extraction_id="synthetic-extraction-001",
        document_id=document_id,
        extractor_id="mock-llm-extractor-v1",
        method=ExtractionMethod.LLM,
        extracted_at=FIXED_TIME + timedelta(minutes=2),
        scheme=scheme,
    )
    validated = ValidatedSchemeCandidate(
        extraction_id=extracted.extraction_id,
        validator_version="local-schema-v1",
        validated_at=FIXED_TIME + timedelta(minutes=3),
        scheme=scheme,
    )
    human = TransitionActor(actor_id="synthetic-reviewer", kind=ActorKind.HUMAN)
    review = HumanReviewApproval(
        review_id="synthetic-review-001",
        reviewer=human,
        reviewed_at=FIXED_TIME + timedelta(minutes=4),
        reviewed_scheme=_reviewed_copy(scheme),
        attested=True,
        note="Reviewed synthetic fixture against all three mock sections.",
    )
    publication = PublicationApproval(
        publication_id="synthetic-publication-001",
        publisher=TransitionActor(actor_id="synthetic-publisher", kind=ActorKind.HUMAN),
        published_at=FIXED_TIME + timedelta(minutes=5),
        attested=True,
    )
    return SyntheticPipelineFixture(
        source=source,
        parsed=parsed,
        extracted=extracted,
        validated=validated,
        review=review,
        publication=publication,
        system_actor=TransitionActor(actor_id="offline-ingestion", kind=ActorKind.SYSTEM),
    )
