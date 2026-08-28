# Codex Start Here

Open this repository in Codex and ask it to read, in order:

1. `AGENTS.md`
2. `README.md`
3. `STRUCTURE.md`
4. `TASKS.md`
5. the design document relevant to the current phase

Do not ask Codex to build the entire project in one pass. Use bounded phases with tests and review at each boundary.

## Recommended first Codex prompt

```text
Read AGENTS.md, README.md, STRUCTURE.md, TASKS.md, docs/01-product-requirements.md,
docs/02-system-architecture.md, docs/03-llm-provider-abstraction.md, and
docs/09-evaluation-plan.md completely before changing anything.

Implement only Phase 0 from TASKS.md.

Requirements:
- preserve all architecture boundaries in AGENTS.md;
- create a production-quality Python backend skeleton and Next.js/TypeScript frontend skeleton;
- add Docker Compose for local development;
- define the canonical domain models and evaluation-case schema;
- add tests for all deterministic models/validation;
- do not implement provider-specific LLM adapters yet;
- do not build polished frontend pages yet;
- document exact commands to run lint, type-check, tests, and local services;
- do not add secrets or real farmer data.

At the end, summarize files changed, architecture decisions, commands run, test results, and any open decisions.
```

After Phase 0 is complete and reviewed, use the prompt files under `codex-prompts/` sequentially.

## Working discipline

At the end of each Codex phase:

- inspect the diff;
- run tests;
- verify dependency direction;
- update docs if contracts changed;
- only then move to the next phase.

The most important rule: do not let convenience collapse the provider abstraction. No OpenAI/Anthropic/Gemini/Ollama SDK imports are allowed outside their adapters.
