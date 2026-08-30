# Backend

Target: Python modular monolith with FastAPI at the transport layer and framework-independent domain services underneath.

Important boundaries:

- API routes translate HTTP/websocket requests into application commands.
- Workflows coordinate typed services and agents.
- Domain models/services must not depend on FastAPI or provider SDKs.
- Provider-specific LLM code belongs only under `llm/providers/`.
- Persistence is accessed through repository interfaces.
- Evaluation code should be able to call application workflows without starting HTTP.

Read `../docs/02-system-architecture.md` and `../docs/03-llm-provider-abstraction.md` before implementing backend code.

## LLM layer

Phase 1 usage, configuration, installation commands, test commands, and the
adapter capability matrix are documented in `../docs/19-llm-adapters.md`.
The runnable example is `examples/llm_usage.py`, configured by
`examples/llm.example.toml`.

## Domain and evaluation foundations

Canonical domain models, the frozen synthetic evaluation schema, fixture path,
and workflow-neutral runner contract are documented in
`../docs/20-domain-and-evaluation.md`.

## Scheme ingestion and retrieval

The source/version persistence ports, explicit review/publish lifecycle, synthetic
fixture, and hybrid retrieval contracts are documented in
`../docs/21-scheme-ingestion-and-retrieval-contracts.md`.

## Text vertical slice

The persistent text workflow, profile merge policy, deterministic/semantic
eligibility boundary, evidence verification, localization, usage example, and E2E
safety tests are documented in `../docs/22-text-vertical-slice.md`.

## Voice boundary

Provider-independent STT/TTS contracts, OpenAI adapters, canonical voice-to-text
workflow integration, configuration, and the capability matrix are documented in
`../docs/23-voice-abstraction.md`. See `examples/voice.example.toml` and
`examples/voice_usage.py`.

## Runtime hardening

The FastAPI safety shell, correlation/logging/metrics boundaries, provider retry
policy, admin RBAC, evidence injection controls, Alembic migration path, Docker
Compose setup, load scaffold, and explicit limitations are documented in
`../docs/24-production-hardening.md`.

Local verification:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check src tests
.venv/bin/mypy src/kisanpath
.venv/bin/pytest
```
