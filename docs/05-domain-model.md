# Domain Model

## Farmer profile

Suggested canonical fields:

```text
state
district
village (optional)
land_area(value, unit, normalized_hectares, confidence)
land_ownership(owner/tenant/sharecropper/other/unknown)
crops[]
irrigation_type
farmer_category
requested_needs[]
preferred_language
confirmed_fields[]
```

Every extracted field should be capable of retaining provenance such as source message ID, source utterance, confidence, and confirmation status.

## Scheme

```text
scheme_id
name
authority
jurisdiction
categories[]
summary
benefits[]
eligibility_rules[]
required_documents[]
application_steps[]
official_sources[]
publication_state
version
```

## Source reference

```text
source_id
document_id
canonical_url or source locator
title
page/section/chunk locator
retrieved/imported metadata
review status
```

Avoid copying large source passages into every row. Store stable locators and bounded excerpts where legally/operationally appropriate.

## Eligibility rule

```text
rule_id
scheme_id
description
rule_type: deterministic | semantic | manual_review
field
operator
expected_value
normalization_rule
required: bool
source_ref
```

Example operators:

```text
eq
neq
in
not_in
lte
lt
gte
gt
between
contains
boolean_true
boolean_false
exists
not_exists
```

## Rule evaluation

```text
rule_id
result: PASS | FAIL | UNKNOWN | MANUAL_REVIEW
farmer_value
normalized_value
explanation
source_ref
evaluator_type
confidence (semantic only)
```

## Scheme evaluation

```text
scheme_id
status
rule_evaluations[]
missing_fields[]
blocking_rule_ids[]
manual_review_rule_ids[]
confidence_summary
```

Do not produce one magic LLM confidence score as a substitute for the individual rule outcomes.

## Conversation

Persist:

```text
conversation_id
preferred_language
current_profile
pending_confirmation
workflow_stage
candidate_scheme_ids
latest_evaluations
created/updated metadata
```

Conversation history may be separately stored, but workflow correctness must not depend on reconstructing canonical state from raw chat messages each turn.

## Implemented foundation contract

The immutable Phase 0 models are implemented under
`backend/src/kisanpath/domain/`. Detailed invariants, fixture locations, and the
evaluation runner boundary are documented in `docs/20-domain-and-evaluation.md`.
