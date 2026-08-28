# Scheme Data Ingestion and Retrieval

## Trust model

Official/public source material may be ingested for extraction, but extracted data is not automatically trusted.

Suggested lifecycle:

```text
RAW
-> PARSED
-> AUTO_EXTRACTED
-> VALIDATED
-> HUMAN_REVIEWED
-> PUBLISHED
-> RETIRED
```

Only `PUBLISHED` scheme versions may drive production/hackathon eligibility results.

## Ingestion steps

1. register source document and provenance;
2. parse text/sections without discarding page/section location;
3. chunk for retrieval with stable IDs;
4. extract candidate scheme metadata and rules through structured LLM output where useful;
5. run local schema/domain validation;
6. flag conflicts/ambiguous rules;
7. human review and edit;
8. publish immutable version;
9. generate embeddings/index entries from published material.

## Frozen hackathon corpus

Create a fixed dataset for judging so results do not change because a webpage was edited or unavailable. Record where each source originated, but use the reviewed local snapshot for evaluation.

## Hybrid retrieval

Use two lanes:

### Structured filters
Examples:
- jurisdiction/state;
- scheme category;
- crop or activity tags;
- ownership/farmer category where safe;
- published/active state.

### Semantic retrieval
Search scheme summaries and approved source chunks for natural user needs such as "drip irrigation support".

Fuse candidate results, then rerank with deterministic signals first. Semantic similarity alone must not imply eligibility.

## Retrieval output

Return scheme IDs plus evidence/context needed for downstream evaluation. Do not return arbitrary unreviewed internet text to the eligibility engine.
