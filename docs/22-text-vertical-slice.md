# First Text Vertical Slice

The first complete text workflow connects structured extraction to a localized,
evidence-backed result while preserving unknowns and deterministic failures. It is
framework-independent and uses synthetic reviewed scheme fixtures in tests.

## Flow and ownership

```text
TextMessage
  -> ProfileExtractor                         agents/ (LLM allowed)
  -> ProfileMerger                           domain/ (deterministic)
  -> confirmation gate                      workflows/ (deterministic)
  -> published-corpus hybrid retrieval      retrieval/
  -> EligibilityEngine
       deterministic rules                  domain/
       semantic rules only -> evaluator     agents/ (LLM allowed)
  -> ClarificationPolicy                    domain/ (deterministic)
  -> EvidenceVerifier                       domain/ (deterministic)
  -> ResponseComposer                       domain/ (evidence-limited)
  -> ResponseLocalizer                      domain/ (deterministic templates)
  -> ConversationRepository                 persistence/
```

No domain or workflow module imports a provider SDK. `LLMProfileExtractor` and
`LLMSemanticRuleEvaluator` depend on the internal `LLMClient` contract and request
locally validated Pydantic structured outputs.

## Explicit state machine

Successful complete turns persist this sequence:

```text
START or waiting state
-> PARSE_INPUT
-> UPDATE_PROFILE
-> DISCOVER_SCHEMES
-> EVALUATE_RULES
-> VERIFY_EVIDENCE
-> COMPOSE_RESPONSE
-> LOCALIZE
-> END
```

Two safe waiting branches are explicit:

```text
UPDATE_PROFILE -> CONFIRM_VALUE
EVALUATE_RULES -> ASK_CLARIFICATION
```

A new text response transitions either waiting state back to `PARSE_INPUT` and
merges new explicit facts into the canonical profile. If a response explicitly
confirms a proposed value, structured extraction lists it in `confirmed_fields`;
the deterministic merger records confirmed provenance and avoids another
confidence prompt.

Every transition increments the conversation revision and appends a
`WorkflowTransition` containing only stage, timestamp, revision, and triggering
message ID. The state machine rejects transitions outside the declared graph.

## Canonical memory

`ConversationState` persists:

- the canonical `FarmerProfile` and fact provenance;
- pending confirmation or clarification;
- candidate scheme IDs;
- latest rule-by-rule `SchemeEvaluation` records;
- latest `ClaimVerificationBatch`;
- the last safe localized response;
- processed message IDs for completed-turn idempotency;
- the operational transition audit.

Correctness does not require replaying LLM messages. The profile extractor receives
only the latest farmer text, current canonical profile, preferred language, and any
pending confirmation. Raw provider output is neither canonical memory nor returned
to clients.

`ConversationRepository` is an async optimistic-concurrency port. The in-memory
implementation supports deterministic tests; durable database storage is a later
adapter task.

## Eligibility safety policy

`EligibilityEngine` refuses unpublished schemes and dispatches by reviewed rule
type:

- `deterministic`: evaluated only by typed comparison code;
- `semantic`: and only this type, may call `SemanticRuleEvaluator`;
- `manual_review`: always produces `MANUAL_REVIEW`.

Missing required facts produce `UNKNOWN`. Optional unknown conditions are skipped
without fabricating a farmer fact. Semantic results below the configured confidence
threshold become `MANUAL_REVIEW`.

Aggregation order is fixed:

```text
any FAIL        -> NOT_ELIGIBLE
else any manual -> MANUAL_REVIEW
else any unknown-> INSUFFICIENT_INFORMATION
else            -> LIKELY_ELIGIBLE
```

This is also enforced by the canonical `SchemeEvaluation` validator, so an
LLM-backed component cannot represent a deterministic FAIL as eligible.

## Evidence and response boundary

The verifier does not reevaluate eligibility. It checks each existing rule result
against the matching reviewed rule and approved source reference. The response
composer includes only scheme-level claims whose complete rule set passed this
provenance check. Unsupported consequential claims are omitted.

Localization uses conservative English, Hindi, and Gujarati templates populated
only with verified scheme name, status, and source IDs. It cannot add new scheme
facts. Retrieval scores remain discovery metadata and never become eligibility
confidence.

## Application usage

```python
workflow = TextEligibilityWorkflow(
    conversations=conversation_repository,
    profile_extractor=LLMProfileExtractor(llm_client),
    profile_merger=ProfileMerger(critical_confidence_threshold=0.8),
    retriever=hybrid_retrieval_service,
    eligibility=EligibilityEngine(
        semantic_evaluator=LLMSemanticRuleEvaluator(llm_client),
        minimum_semantic_confidence=0.7,
    ),
)

await workflow.create_conversation(
    "conversation-001",
    preferred_language=LanguageCode.GUJARATI,
)
result = await workflow.handle_text(
    "conversation-001",
    TextMessage(
        message_id="message-001",
        text="મારી પાસે 1.5 હેક્ટર જમીન છે અને મને ડ્રિપ સિંચાઈ સહાય જોઈએ છે.",
        language_hint=LanguageCode.GUJARATI,
    ),
)
```

Submitting the same completed `message_id` returns the persisted response without
rerunning extraction or providers.

## Test coverage

The suite includes:

- deterministic profile merge, contradiction, confidence, and confirmation tests;
- deterministic numeric eligibility comparisons and unknown handling;
- proof that semantic evaluation is not called for deterministic rules;
- semantic confidence-to-manual-review behavior;
- conversation optimistic-concurrency tests;
- an end-to-end missing-land case that stops at clarification rather than guessing;
- an end-to-end mixed-rule case where an LLM-backed semantic PASS cannot override
  a deterministic FAIL;
- explicit state transition and completed-message idempotency assertions.

Real farmer PII and real scheme acquisition are outside these fixtures.
