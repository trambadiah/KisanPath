# AGENTS.md - Mandatory instructions for Codex

This file defines non-negotiable implementation rules for any coding agent working on KisanPath. Read this file, `README.md`, `STRUCTURE.md`, `TASKS.md`, and the relevant design document before modifying code.

## Mission

Build KisanPath as a production-oriented, multilingual, voice-first, evidence-grounded government-scheme discovery and eligibility-assistance platform for Indian farmers.

The product must remain safe, auditable, reproducible, and provider-agnostic.

## Non-negotiable architecture rules

### 1. Never call an LLM provider SDK from domain or agent code

Allowed dependency direction:

```text
agents/domain -> internal LLM interfaces -> provider adapters -> provider SDK
```

Forbidden:

```text
profile_agent.py -> OpenAI SDK
eligibility_service.py -> Anthropic SDK
```

Only modules under `backend/src/kisanpath/llm/providers/` may directly import provider SDKs.

### 2. Never call STT/TTS vendor SDKs outside voice adapters

Only `voice/stt/providers` and `voice/tts/providers` implementations may know vendor-specific APIs.

### 3. Do not make every component an agent

Use deterministic application services for:

- explicit eligibility comparisons;
- unit normalization;
- state/district normalization;
- data validation;
- schema validation;
- source/provenance enforcement;
- deduplication;
- confidence thresholds;
- workflow state transitions.

Use LLM reasoning only where language ambiguity or semantic interpretation actually requires it.

### 4. An LLM can never override a deterministic FAIL

If a structured eligibility rule evaluates to `FAIL`, no generative component may change it to `PASS` or `LIKELY_ELIGIBLE`.

### 5. Unknown must remain unknown

If required facts are missing, produce `UNKNOWN`, `INSUFFICIENT_INFORMATION`, or `MANUAL_REVIEW`. Never fill missing farmer facts from assumptions.

### 6. All user-visible scheme claims need provenance

Every important factual claim must reference an approved scheme source or derive directly from a deterministic rule whose source is recorded.

Unsupported important claims must be removed before the final response.

### 7. Do not expose chain-of-thought

Store operational traces only:

- prompt/version identifiers;
- input/output schemas;
- tool calls and tool results;
- state transitions;
- rule evaluations;
- citations;
- retry/error metadata;
- concise machine-generated explanations intended for audit.

Do not persist or expose hidden chain-of-thought reasoning.

### 8. Keep the baseline independent

The baseline must remain runnable without final-system features such as the rule engine, verifier, or orchestration enhancements. It must use the same frozen data/evaluation cases for fair comparison.

### 9. Every meaningful implementation experiment updates the improvement changelog

When a change is intended to improve quality, record:

- what changed;
- why;
- evaluation result;
- whether it was kept/revised/removed;
- what was learned.

Use `docs/14-improvement-changelog-template.md`.

### 10. Prefer typed boundaries

Use Pydantic/dataclasses or equivalent typed models at all module boundaries. Avoid passing large unstructured dictionaries between services.

## Coding expectations

- Keep business logic framework-independent.
- Prefer dependency injection over global clients.
- Use async I/O for external providers and network-bound storage.
- Add unit tests for deterministic code.
- Add contract tests for every provider adapter.
- Add integration tests around repositories and retrieval.
- Add an E2E test for the main farmer journey.
- Add schema validation to every structured LLM output.
- Map provider errors to KisanPath-owned exception classes.
- No secrets, tokens, private credentials, or real farmer PII in the repository.
- Use synthetic test data by default.
- Log structured metadata, not raw private audio or sensitive content unless explicitly configured for a safe environment.

## Frontend requirements

The frontend must feel premium, calm, modern, and trustworthy rather than like a generic government portal or agriculture template.

Follow `docs/08-frontend-design-system.md` exactly. Key rules:

- voice-first assistant experience is the visual centerpiece;
- use a deep dark visual foundation with refined agricultural accents;
- avoid cartoon tractors, leaf overload, stock-photo-heavy layouts, and loud green gradients;
- use generous whitespace, strong typography, soft depth, subtle motion, and high-contrast evidence cards;
- accessibility and mobile usage are first-class;
- critical eligibility states must not rely on color alone;
- design for Gujarati/Hindi typography and longer translated strings from the start.

## Before implementing a task

1. Identify the owning module.
2. Read its design doc.
3. Confirm interfaces and dependency direction.
4. Add/update tests with the implementation.
5. Run the relevant test suite.
6. Update docs if public contracts changed.
7. Update the changelog if the change is an experiment affecting measured quality.

## Definition of a good Codex change

A change is not complete just because it runs locally. It is complete when:

- architecture boundaries remain intact;
- tests cover the behavior;
- failure modes are explicit;
- user-visible claims remain evidence-grounded;
- configuration is documented;
- another developer can reproduce it from a clean checkout.
