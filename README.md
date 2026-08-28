# KisanPath

KisanPath is a multilingual, voice-first, evidence-grounded agentic assistant for helping Indian farmers discover government agricultural schemes and understand whether they appear to satisfy published eligibility conditions.

This repository is intentionally structured as a production-oriented modular monolith that can be built incrementally for the hackathon while preserving clean boundaries for later scale. The system is designed around a provider-agnostic LLM layer, deterministic eligibility rules where possible, evidence-backed recommendations, multilingual voice/text interaction, reproducible evaluation, and auditable agent trajectories.

## Core product promise

A farmer should be able to speak naturally in Gujarati, Hindi, or English, describe their farm and need, answer a small number of clarification questions, and receive:

- relevant schemes ranked by fit;
- a condition-by-condition eligibility assessment;
- explicit unknowns and missing information rather than guesses;
- a document/application-readiness checklist;
- citations to approved official source material;
- a concise explanation in the farmer's preferred language;
- optional spoken output.

KisanPath does not make an official government eligibility determination and does not automatically submit applications or take financial/legal actions.

## Architectural principles

1. **LLM providers are adapters, not architecture.** Domain code depends only on KisanPath interfaces. OpenAI, Anthropic, Gemini, Ollama, and future providers are interchangeable.
2. **Deterministic logic beats generative reasoning for explicit rules.** If a condition is a structured comparison, it must be evaluated by code.
3. **Every consequential claim must be evidence-backed.** Unsupported claims are blocked or clearly marked uncertain.
4. **Application state is canonical.** Conversation state, farmer profile, rule outcomes, and sources are stored in structured models, not only in LLM history.
5. **Unknown is a valid outcome.** Missing data must produce `INSUFFICIENT_INFORMATION` rather than a guessed eligibility decision.
6. **Voice is an interface, not a separate reasoning system.** Audio is converted to normalized text/profile facts, then follows the same workflow as typed input.
7. **Evaluation is a product subsystem.** Baseline and final workflows run against the same frozen cases and data.
8. **Hackathon reproducibility is preserved.** The demo can run from a clean environment with a frozen scheme dataset and deterministic evaluation configuration.

## High-level flow

```text
Farmer voice/text
      |
      v
Input + Voice Adapters
      |
      v
Conversation Orchestrator
      |
      v
Profile Extraction / Confirmation
      |
      v
Scheme Discovery
      |
      v
Eligibility Engine
  | deterministic rules
  | semantic fallback
      |
      v
Evidence Verification
      |
      v
Localized Response Composer
      |
      v
Text + optional TTS
```

## Repository map

See `STRUCTURE.md` for the full intended structure and module ownership.

## Read these first

1. `AGENTS.md` - mandatory instructions for Codex and coding agents.
2. `TASKS.md` - ordered implementation backlog with acceptance criteria.
3. `docs/01-product-requirements.md` - product scope and user journeys.
4. `docs/02-system-architecture.md` - target architecture and boundaries.
5. `docs/03-llm-provider-abstraction.md` - provider-agnostic LLM design.
6. `docs/08-frontend-design-system.md` - premium frontend direction.
7. `docs/09-evaluation-plan.md` - baseline, metrics, and gold cases.

## Recommended implementation strategy

Build one vertical slice end to end before broadening scope:

```text
Typed Gujarati/English input
-> profile extraction
-> one frozen scheme
-> deterministic eligibility
-> evidence-backed response
-> evaluation case
```

Then add multi-scheme retrieval, verification, multilingual voice, richer UI, observability, and production hardening.

## Initial hackathon scope

- Geography: Gujarat plus selected central schemes relevant to Gujarat farmers.
- Languages: Gujarati, Hindi, English.
- Scheme corpus: approximately 20-30 carefully reviewed schemes.
- Evaluation: approximately 40 synthetic farmer cases, including ambiguous and adversarial cases.
- Voice: push-to-talk, transcript confirmation for critical fields.
- LLM providers: OpenAI, Anthropic, Gemini, Ollama, plus a generic OpenAI-compatible adapter.

## Non-goals for the first release

- official eligibility decisions;
- automatic government application submission;
- storing Aadhaar or unnecessary identity data;
- unrestricted live-web scheme ingestion into the trusted corpus;
- nationwide coverage before evaluation quality is established;
- using an LLM to override deterministic rule failures.
