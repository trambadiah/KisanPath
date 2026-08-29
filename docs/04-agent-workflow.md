# Agent and Workflow Design

## Principle

KisanPath is an agentic workflow, not an agent swarm. Each LLM-backed component must have a narrow reason to exist and measurable value.

## Profile Agent

### Input
- current conversation state;
- latest normalized transcript/text;
- current structured farmer profile.

### Output
- extracted field updates with confidence/source utterance;
- contradictions;
- suggested clarification fields;
- language/locale hints.

### Must not
- decide scheme eligibility;
- invent missing farmer values;
- call scheme sources directly.

## Scheme Discovery

Prefer deterministic/retrieval service rather than autonomous agent.

Inputs:
- farmer profile;
- declared need;
- jurisdiction;
- reviewed scheme index.

Outputs:
- ranked candidate scheme IDs;
- retrieval rationale metadata;
- source refs.

## Eligibility Engine

Deterministic service for structured conditions. Semantic sub-evaluator only for rules explicitly tagged `semantic`.

Rule result values:

```text
PASS
FAIL
UNKNOWN
MANUAL_REVIEW
```

Overall scheme values:

```text
LIKELY_ELIGIBLE
NOT_ELIGIBLE
INSUFFICIENT_INFORMATION
MANUAL_REVIEW
```

## Verification Agent

Receives draft claims plus approved evidence. It verifies support; it does not independently reinvent eligibility.

Claim values:

```text
SUPPORTED
UNSUPPORTED
CONTRADICTED
UNCERTAIN
```

Unsupported consequential claims are blocked from final output.

## Response Composer

Transforms already-evaluated structured results into user-friendly language. It is not allowed to add new scheme facts beyond provided structured evidence.

## Clarification policy

Prefer questions that maximize information gain:

1. required missing fields affecting multiple candidate schemes;
2. fields that can switch a likely result to fail/pass;
3. critical values requiring confirmation;
4. optional tailoring information last.

Avoid interrogating the farmer for fields that do not influence current results.

## Voice confirmation

Critical values from ASR should retain transcript source and confidence. Confirm when confidence is below threshold, transcript is ambiguous, unit is regional/variable, or a large numerical difference could change eligibility.

Example:

```text
"I heard your land area as 3 acres. Is that correct?"
```

Do not normalize ambiguous regional units such as bigha without enough geographic context.

## Implemented text vertical slice

The first framework-independent text workflow is implemented under
`backend/src/kisanpath/workflows/`. It follows the explicit state machine and
persists every canonical transition through `ConversationRepository`.

LLM-backed components are limited to structured profile extraction and rules
explicitly marked `semantic`. Profile merging, critical-value thresholds,
contradiction preservation, clarification selection, deterministic rule
comparisons, result aggregation, provenance verification, localization templates,
and state transitions are deterministic services.

See `docs/22-text-vertical-slice.md` for the dependency graph, persistence model,
usage example, and tested safety properties.

## Implemented voice entry point

`VoiceEligibilityWorkflow` transcribes through the provider-independent `STTClient`
port and passes the normalized transcript to the same `TextEligibilityWorkflow` used
by typed input. ASR confidence, segments, ambiguity alternatives, provider, and model
are carried as trusted merge provenance. Critical ambiguity and regional land units
stop at the existing `CONFIRM_VALUE` state. Optional localized audio is produced
through the provider-independent `TTSClient` port.

See `docs/23-voice-abstraction.md` for configuration, contracts, usage, capability
matrix, and test coverage.
