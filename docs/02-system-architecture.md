# System Architecture

## Architectural style

Start as a modular monolith with explicit internal interfaces. This minimizes operational complexity for the hackathon while preserving extraction points for future services.

## Context diagram

```text
Farmer / Judge / Admin
          |
          v
   Web / Mobile UI
          |
          v
      API Layer
          |
          v
 Conversation Workflow
          |
   +------+------+----------------------+----------------+
   |             |                      |                |
   v             v                      v                v
Profile       Retrieval           Eligibility       Verification
Agent         Services             Engine             Agent
   |             |                      |                |
   +-------------+-----------+----------+----------------+
                             |
                             v
                     Response Composer
                             |
                  +----------+----------+
                  |                     |
                  v                     v
                Text                   TTS
```

## Infrastructure dependencies

```text
PostgreSQL (+ pgvector initially)
Redis for ephemeral cache/locks/jobs
Object storage abstraction for source documents/audio if needed
External/local LLM providers through LLMClient
External/local STT/TTS providers through voice interfaces
```

## Module rules

### API
No business logic. Validates transport input, calls application/workflow services, maps typed errors to API responses.

### Domain
Pure models and deterministic business rules. No provider SDKs, no FastAPI imports, no database-driver imports.

### Workflows
Own explicit orchestration and state transitions. The primary farmer assistance flow should be a transparent state machine rather than unconstrained agent-to-agent chat.

### Agents
LLM-backed components have narrow typed contracts. They should not own persistent state directly.

### Persistence
Repository interfaces separate domain/application code from PostgreSQL. Use transactions where one logical workflow update spans multiple writes.

### Retrieval
Hybrid retrieval combines structured filters with semantic search. All results preserve source IDs and reviewed/published state.

## Conversation state machine

```text
START
  |
  v
PARSE_INPUT
  |
  v
UPDATE_PROFILE
  |
  +--> CONFIRM_VALUE ----+
  |                       |
  +--> ASK_CLARIFICATION -+
  |                       |
  v                       |
DISCOVER_SCHEMES <--------+
  |
  v
EVALUATE_RULES
  |
  +--> ASK_CLARIFICATION --> EVALUATE_RULES
  |
  v
VERIFY_EVIDENCE
  |
  v
COMPOSE_RESPONSE
  |
  v
LOCALIZE
  |
  +--> SYNTHESIZE_AUDIO (optional)
  |
  v
END
```

## Scaling path

Only extract services when operational reasons justify it. Likely future extraction candidates:

- ingestion/refresh worker;
- voice processing;
- high-volume evaluation runner;
- retrieval/search service.

Do not split the eligibility engine from the core application prematurely because consistency and auditability are more valuable than service count.
