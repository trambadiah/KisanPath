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
