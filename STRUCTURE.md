# Repository Structure

```text
kisanpath/
|
|-- README.md
|-- AGENTS.md
|-- TASKS.md
|-- STRUCTURE.md
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
|
|-- backend/
|   |-- pyproject.toml
|   |-- README.md
|   |-- src/kisanpath/
|   |   |-- api/                 # FastAPI routes, dependencies, transport schemas
|   |   |-- domain/              # Pure business/domain models and services
|   |   |-- agents/              # LLM-backed role components only
|   |   |-- workflows/           # Explicit state machines/orchestration
|   |   |-- llm/
|   |   |   |-- base.py          # LLMClient protocol
|   |   |   |-- models.py        # Canonical request/response/capability models
|   |   |   |-- registry.py      # provider registration/factories
|   |   |   |-- router.py        # routing/fallback/policy
|   |   |   |-- providers/       # OpenAI, Anthropic, Gemini, Ollama, compatible
|   |   |   `-- middleware/      # tracing/retry/cache/rate limits
|   |   |-- voice/
|   |   |   |-- stt/             # canonical STT interface + provider adapters
|   |   |   `-- tts/             # canonical TTS interface + provider adapters
|   |   |-- retrieval/           # structured + semantic scheme retrieval
|   |   |-- ingestion/           # official document -> reviewed canonical scheme
|   |   |-- persistence/         # repositories and DB adapters
|   |   |-- observability/       # logs/metrics/tracing
|   |   `-- security/            # auth, redaction, injection controls
|   `-- tests/
|       |-- unit/
|       |-- integration/
|       |-- contract/
|       `-- e2e/
|
|-- frontend/
|   |-- README.md
|   |-- app/                      # Next.js app router/pages/layouts
|   |-- components/               # reusable visual + product components
|   |-- lib/                      # API client, state, localization, helpers
|   `-- public/                   # icons/assets only; no sensitive data
|
|-- prompts/
|   |-- profile/                  # versioned profile extraction prompts
|   |-- verifier/                 # versioned evidence verification prompts
|   `-- response/                 # localized response composition prompts
|
|-- data/
|   |-- raw/                      # source docs for local/dev; trusted origin only
|   |-- reviewed/                 # human-reviewed normalized scheme fixtures
|   `-- evaluation/               # frozen synthetic gold cases
|
|-- evaluation/                   # runner, metrics, reports, baseline comparison
|-- trajectories/                 # representative sanitized agent/tool traces
|-- docs/                         # design and hackathon documentation
|-- scripts/                      # setup/import/eval helper scripts
`-- infra/                        # deployment/IaC added after application stabilizes
```

## Boundary ownership

### `domain/`
Must not import FastAPI, vendor SDKs, database drivers, or orchestration frameworks. It defines canonical concepts such as `FarmerProfile`, `Scheme`, `EligibilityRule`, `RuleEvaluation`, and `SchemeEvaluation`.

### `agents/`
Contains only components where language-model reasoning provides real value. An agent receives typed state/context and returns typed results.

### `workflows/`
Owns execution order and state transitions. It can call domain services and agents through interfaces but should not contain provider-specific code.

### `llm/`
Owns the entire provider abstraction. Provider SDKs must remain isolated under `providers/`.

### `retrieval/`
Owns discovery of candidate schemes. It should combine structured filters and semantic retrieval rather than depend on vector similarity alone.

### `ingestion/`
Converts approved source material into reviewable canonical scheme records. Publishing new trusted scheme data requires an explicit review state transition.

### `evaluation/`
Is independent of production APIs. It can run frozen cases directly against baseline/final workflows and export machine-readable and human-readable reports.
