# Implementation Plan for Codex

Implement in order. Do not skip directly to the polished UI before a complete, testable vertical slice exists.

## Phase 0 - Foundations

### Task 0.1 Repository bootstrap
- Initialize backend Python package and frontend application.
- Add local Docker Compose for backend, frontend, PostgreSQL, Redis, and optional Ollama profile.
- Add `.env.example` with provider placeholders only.
- Add CI commands for lint, type-check, tests, and build.

**Acceptance:** clean checkout can start required local dependencies and both applications expose health pages/endpoints.

### Task 0.2 Canonical domain models
Implement typed models for:
- farmer profile and extracted fields;
- land area and unit normalization;
- scheme/source/version;
- eligibility rule;
- rule evaluation;
- scheme evaluation;
- conversation state;
- claim verification.

**Acceptance:** deterministic unit tests cover validation and serialization.

### Task 0.3 Evaluation schema first
Define frozen synthetic case schema before the advanced workflow exists.

**Acceptance:** at least five seed cases load and validate; format supports expected scheme/rule outcomes and missing-information cases.

## Phase 1 - Provider-agnostic LLM layer

### Task 1.1 Core interfaces
Implement `LLMClient`, canonical requests/responses, structured-output requests, capabilities, normalized usage, and KisanPath exception hierarchy.

### Task 1.2 Registry and configuration
Implement provider registry, configuration loader, per-agent provider selection, capability validation, and secret-from-environment behavior.

### Task 1.3 Provider adapters
Implement:
- OpenAI;
- Anthropic;
- Gemini;
- Ollama;
- generic OpenAI-compatible endpoint.

### Task 1.4 Contract tests
Run a shared contract suite against adapters. Network/live tests should be opt-in; mocked tests must run in CI.

**Phase acceptance:** changing a config file can route the same agent to another provider without changing agent code.

## Phase 2 - Scheme corpus and ingestion

### Task 2.1 Canonical scheme model persistence
Store schemes, versions, rules, documents, chunks, and provenance.

### Task 2.2 Offline ingestion pipeline
Implement parse -> extract -> validate -> review -> publish states.

### Task 2.3 Frozen demo corpus
Curate the initial Gujarat + selected central scheme corpus. Store source provenance and reviewed eligibility rules.

**Phase acceptance:** every published rule links to an approved source location.

## Phase 3 - Baseline

Implement a single-prompt baseline using the same LLM abstraction and frozen source material, without the final deterministic rule engine or verifier.

**Acceptance:** evaluation runner can execute baseline on all seed cases and store result, latency, usage, and errors.

## Phase 4 - Farmer profile workflow

### Task 4.1 Text extraction
Extract structured facts from Gujarati, Hindi, and English input.

### Task 4.2 Merge and contradiction detection
Merge new facts into canonical profile without overwriting conflicting facts silently.

### Task 4.3 Critical-field confirmation
Require explicit confirmation for critical voice-derived fields such as location and land area when confidence is insufficient.

### Task 4.4 Clarification policy
Ask the minimum next question that changes eligibility/discovery outcome.

**Acceptance:** ambiguous inputs produce clarification rather than guessed facts.

## Phase 5 - Scheme discovery

Implement:
- structured filtering by jurisdiction/category/profile;
- semantic retrieval over approved source chunks;
- candidate fusion/ranking;
- source-aware result model.

**Acceptance:** discovery recall@K is measurable on gold cases.

## Phase 6 - Eligibility engine

### Task 6.1 Deterministic evaluator
Support typed operators such as equality, membership, threshold, range, boolean, date-window, and missing-field handling.

### Task 6.2 Semantic fallback
Route only non-structurable conditions to an LLM-backed semantic evaluator with typed output and confidence threshold.

### Task 6.3 Aggregation policy
Produce one of:
- `LIKELY_ELIGIBLE`;
- `NOT_ELIGIBLE`;
- `INSUFFICIENT_INFORMATION`;
- `MANUAL_REVIEW`.

**Acceptance:** deterministic FAIL cannot be overridden by an LLM result.

## Phase 7 - Evidence verifier

- Extract important claims from the draft response.
- Match each claim to scheme/rule/source evidence.
- Mark supported, unsupported, contradicted, or uncertain.
- Block unsupported consequential claims.

**Acceptance:** user-facing eligibility claims can be traced to provenance in the returned API model.

## Phase 8 - Conversation orchestrator

Implement explicit state machine:

```text
PARSE_INPUT
-> UPDATE_PROFILE
-> CONFIRM_VALUE? / ASK_CLARIFICATION?
-> DISCOVER_SCHEMES
-> EVALUATE_RULES
-> ASK_CLARIFICATION?
-> VERIFY_EVIDENCE
-> COMPOSE_RESPONSE
-> LOCALIZE
-> END
```

Persist workflow state and make retries idempotent where feasible.

## Phase 9 - Voice

### Task 9.1 STT abstraction
Provider-independent transcript model with language hint, confidence metadata, timestamps if available.

### Task 9.2 TTS abstraction
Provider-independent synthesis model.

### Task 9.3 Voice UX
Push-to-talk, transcript preview, critical-value confirmation, cancel/retry, text fallback.

**Acceptance:** a Gujarati voice journey reaches the same canonical workflow as typed input.

## Phase 10 - Premium frontend

Build according to `docs/08-frontend-design-system.md`.

Priority screens:
1. landing;
2. assistant/voice conversation;
3. scheme recommendation results;
4. scheme evidence drawer/detail;
5. farmer profile confirmation sheet;
6. evaluation/admin demo page for judges.

**Acceptance:** responsive mobile-first experience, keyboard accessible, Gujarati/Hindi tested, loading/error states polished.

## Phase 11 - Evaluation and improvement loop

Expand to approximately 40 synthetic cases and run baseline vs each meaningful iteration.

Report:
- eligibility classification accuracy;
- false eligibility rate;
- missing-information detection;
- scheme discovery recall@K;
- citation precision;
- unsupported-claim rate;
- profile extraction accuracy;
- critical-field ASR accuracy;
- completion time;
- LLM usage/cost estimate.

Update `docs/14-improvement-changelog-template.md` after each experimental iteration.

## Phase 12 - Production hardening

- structured logging;
- OpenTelemetry-compatible traces;
- metrics dashboards contract;
- rate limiting;
- admin RBAC;
- secrets management integration points;
- prompt-injection defenses;
- payload/audio size limits;
- audit events;
- DB migrations;
- backup/restore notes;
- load tests;
- provider outage/fallback tests;
- threat model review.

## Phase 13 - Hackathon package

Complete:
- production-quality README;
- improvement changelog;
- reproduction guide;
- representative trajectories for every LLM-backed agent;
- baseline/final evaluation report;
- five-minute demo script and assets;
- explicit hot take / main failure mode.
