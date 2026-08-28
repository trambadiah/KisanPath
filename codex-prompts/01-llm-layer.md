# Codex Prompt - LLM Layer

Read AGENTS.md and docs/03-llm-provider-abstraction.md.

Implement Phase 1 from TASKS.md only.

Build the provider-agnostic LLM abstraction, canonical request/response models, structured output contract, capability model, registry, configuration, router boundary, normalized internal exception hierarchy, and shared provider contract-test harness.

Then implement adapters for OpenAI, Anthropic, Gemini, Ollama, and a generic OpenAI-compatible endpoint behind the same interface.

Constraints:
- no agent/domain code may import provider SDKs;
- secrets come only from runtime configuration/environment;
- provider errors must be normalized;
- structured responses must be validated locally;
- live provider tests must be opt-in and skipped cleanly without credentials;
- mocked contract tests must run in CI;
- evaluation fallback must be configurable off.

Finish with tests, usage examples, and a concise adapter capability matrix.
