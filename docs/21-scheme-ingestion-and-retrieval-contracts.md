# Scheme Ingestion and Retrieval Contracts

This phase establishes the trusted-data boundary; it does not curate or import any
real government scheme. Tests use a clearly labelled fictional policy with no
farmer PII.

## Trust lifecycle

| State | Produced by | Eligibility-visible |
| --- | --- | --- |
| `RAW` | source registration | No |
| `PARSED` | parser adapter | No |
| `AUTO_EXTRACTED` | deterministic or LLM extractor | No |
| `VALIDATED` | local schema/domain validator | No |
| `HUMAN_REVIEWED` | attested human review and edits | No |
| `PUBLISHED` | separate attested human publication action | Yes |
| `RETIRED` | explicit retirement action | No (history retained) |

The lifecycle is append-audited and immutable: each transition returns a new
`IngestionRecord`, increments its optimistic-concurrency revision, and appends an
operational event. States cannot be skipped. Blocking validation issues must be
explicitly resolved in the human review record.

LLM extraction never changes trust. `ExtractedSchemeCandidate` and
`ValidatedSchemeCandidate` require the embedded canonical scheme to remain
`DRAFT`. Human review supplies an edited `IN_REVIEW` snapshot with approved source
references. Publication reruns canonical model validation before constructing a
`PublishedSchemeVersion`.

## Persistence boundaries

- `SourceDocumentRecord` stores immutable acquisition provenance and a SHA-256
  digest of the frozen snapshot.
- `ParsedDocumentChunk` stores untrusted text with stable document, source,
  location, and ordinal identifiers.
- `PublishedSchemeVersion` is the eligibility-visible scheme/version/rule
  projection and links back to its human review.
- `PublishedDocumentChunk` is created only alongside publication and links every
  retrieval excerpt to scheme, version, publication, document, and source IDs.
- `SourceDocumentRepository`, `IngestionRepository`, and
  `PublishedCorpusRepository` are async ports. Concrete SQL/object/vector storage
  can implement them without changing domain or ingestion code.
- `PublicationUnitOfWork` couples lifecycle persistence with corpus publication or
  retirement. The in-memory implementation provides this atomically for tests.

The in-memory adapter is for deterministic tests and local examples, not durable
production storage.

## Ingestion usage

Adapters implement the ports in `kisanpath.ingestion.base`. After parse,
extraction, and local validation, application code applies explicit transitions:

```python
record = IngestionLifecycle.register(
    ingestion_id="ing-001",
    source_document=source,
    actor=offline_worker,
    occurred_at=registered_at,
)
record = IngestionLifecycle.record_parsed(
    record, parsed, actor=offline_worker, occurred_at=parsed_at
)
record = IngestionLifecycle.record_extraction(
    record, extracted, actor=offline_worker, occurred_at=extracted_at
)
record = IngestionLifecycle.record_validation(
    record, validated, actor=offline_worker, occurred_at=validated_at
)

# These are separate human-owned commands; neither is inferred from extraction.
record = IngestionLifecycle.record_human_review(record, human_review_approval)
published_record, publication, chunks = IngestionLifecycle.publish(
    record, publication_approval
)

await unit_of_work.commit_publication(
    published_record,
    publication,
    chunks,
    expected_revision=record.revision,
)
```

Application authentication/RBAC must create the human actor records in a later API
phase. An extractor or background worker cannot pass a `SYSTEM` actor through the
review or publication models.

## Hybrid retrieval

`StructuredSchemeRetriever` and `SemanticSchemeRetriever` are independent async
ports. `HybridRetrievalService` executes both, then:

1. verifies every lane result against the authoritative active published corpus;
2. rejects retired, draft, unknown, or mismatched publication identities;
3. deduplicates scheme/version candidates;
4. resolves excerpts only from published chunks;
5. ranks candidates with deterministic structured matches before semantic-only
   matches;
6. returns `decision_scope="discovery_only"` and no eligibility field.

```python
service = HybridRetrievalService(
    corpus=published_corpus,
    structured=structured_retriever,
    semantic=vector_retriever,
)
results = await service.search(
    RetrievalQuery(
        text="micro-irrigation support",
        filters=RetrievalFilters(state="Gujarat"),
        top_k=5,
    )
)
```

Semantic similarity is discovery evidence only. A later eligibility engine must
evaluate the canonical rules independently and may never convert retrieval scores
into eligibility outcomes.

## Synthetic test data

`backend/tests/fixtures/synthetic_scheme_document.json` contains a mock source
snapshot and stable chunks. It is explicitly marked synthetic and describes no
real programme or person. Unit and integration tests cover lifecycle ordering,
human gates, blocking issues, provenance completeness, concurrency, publication,
retirement, active-corpus filtering, evidence resolution, and deterministic-first
ranking.
