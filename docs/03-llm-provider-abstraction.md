# LLM Provider Abstraction

## Goal

Any KisanPath agent must be able to use OpenAI, Anthropic, Gemini, Ollama, or another compatible model without changing agent/domain code.

## Canonical interface

Implement a KisanPath-owned protocol similar to:

```python
class LLMClient(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    async def generate_structured(self, request: StructuredLLMRequest[T]) -> T: ...
    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamEvent]: ...
    async def healthcheck(self) -> ProviderHealth: ...
```

## Canonical models

`LLMRequest` should include:

- canonical messages;
- optional model override;
- temperature;
- max output tokens;
- tool definitions if needed;
- timeout;
- request metadata.

`LLMResponse` should include:

- text;
- provider;
- model;
- finish reason;
- normalized token/usage information;
- latency;
- non-sensitive provider metadata.

`StructuredLLMRequest[T]` should include a runtime output schema based on a Pydantic model or equivalent.

## Capability model

Do not assume all providers/models support the same behavior.

```text
streaming
structured_output
native_tools
vision
system_messages
max_context_tokens
```

Validate required capabilities at startup when possible.

## Provider adapters

```text
llm/providers/openai.py
llm/providers/anthropic.py
llm/providers/gemini.py
llm/providers/ollama.py
llm/providers/openai_compatible.py
```

Each adapter is responsible for:

- translating canonical messages;
- mapping tool/schema requests;
- handling provider authentication;
- converting provider errors to internal exceptions;
- normalizing usage and finish reasons;
- preserving cancellation/timeouts;
- never leaking secrets in logs.

## Provider registry

Use configuration + factories rather than scattered conditionals.

```text
registry.register("openai", OpenAIClientFactory)
registry.register("anthropic", AnthropicClientFactory)
...
```

## Per-agent routing

Configuration should permit:

```yaml
llm:
  default:
    provider: openai
    model: default-model

  agents:
    profile:
      provider: gemini
      model: profile-model
    verifier:
      provider: anthropic
      model: verifier-model
    response:
      provider: ollama
      model: local-model
```

No agent code changes are required when this file changes.

## Fallback policy

Production mode may support primary/fallback providers through an `LLMRouter`. Evaluation mode should generally disable fallback or record it explicitly to preserve reproducibility.

Fallback is appropriate for provider unavailability, not for hiding semantic errors.

## Middleware

Recommended wrapper chain:

```text
Agent
-> trace wrapper
-> metric/cost wrapper
-> retry wrapper
-> rate-limit wrapper
-> cache wrapper (safe calls only)
-> provider adapter
```

Avoid caching personalized conversation responses unless the cache key and privacy behavior are carefully defined. Deterministic extraction of static scheme documents can be cached more safely.

## Internal exception hierarchy

At minimum:

```text
LLMError
LLMTimeoutError
LLMRateLimitError
LLMAuthenticationError
LLMUnavailableError
LLMInvalidResponseError
LLMSchemaValidationError
LLMCapabilityError
```

## Structured-output strategy

Use the strongest native schema mechanism offered by each provider. If unavailable, use a strict JSON/schema prompt followed by local parse/validation and a bounded repair attempt.

Never pass an unvalidated structured LLM result into the eligibility engine.

## Contract test suite

Every adapter must run against the same behavioral tests:

- plain generation;
- structured generation;
- invalid schema behavior;
- timeout mapping;
- cancellation;
- streaming normalization;
- tool-call normalization if supported;
- usage normalization;
- provider error mapping;
- healthcheck.

## Implemented Phase 1 contract

The implementation lives under `backend/src/kisanpath/llm/`. Configuration and
usage examples are in `backend/examples/`, while the concise adapter capability
matrix and verification commands are maintained in `docs/19-llm-adapters.md`.

Mocked contract tests are mandatory in CI. Live provider smoke tests require the
explicit `KISANPATH_RUN_LIVE_LLM_TESTS=1` opt-in and skip when their model or
credentials are not configured.
