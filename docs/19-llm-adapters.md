# LLM adapters

KisanPath code outside `backend/src/kisanpath/llm/providers/` consumes only the
canonical `LLMClient` protocol. Provider selection, models, and fallback policy
are runtime configuration; credentials are environment-variable values named by
`api_key_env` and must never appear in TOML.

## Capability matrix

Capabilities can vary by model and compatible endpoint. This matrix describes
what each adapter can normalize when the selected model supports it.

| Adapter | Async generation | Streaming | Structured output | Native tools | System messages | Vision |
|---|---:|---:|---:|---:|---:|---:|
| OpenAI | Yes | Yes | Native JSON schema + local validation | Yes | Yes | Not exposed yet |
| Anthropic | Yes | Yes | Native JSON schema + local validation | Yes | Yes | Not exposed yet |
| Gemini | Yes | Yes | Native JSON schema + local validation | Yes | Yes | Not exposed yet |
| Ollama | Yes | Yes | Native `format` schema + local validation | Yes | Yes | Not exposed yet |
| OpenAI-compatible | Yes | Yes | Endpoint-dependent JSON schema + local validation | Endpoint-dependent | Yes | Not exposed yet |

Override a compatible endpoint's declared capabilities in its provider config.
The router checks route requirements before sending a request. A request with
tools also requires `native_tools`, and structured generation requires
`structured_output`.

The generic compatible adapter defaults `structured_output` and `native_tools`
to `false` because those extensions are not universal. Enable them only for an
endpoint whose contract has been verified.

## Configuration

See `backend/examples/llm.example.toml`. Route provider names refer to aliases in
`llm.providers`, so two aliases may use the same adapter with different models or
endpoints. `llm.agents` overrides the default route without changing agent code.

Fallback occurs only for normalized timeout, rate-limit, or unavailability
errors. Authentication, capability, invalid-response, and schema-validation
errors never trigger fallback. Evaluation mode uses
`evaluation_fallback_enabled`, which defaults to `false`, independently of the
production fallback switch.

## Installation and checks

From `backend/`:

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src/kisanpath
```

Install live SDKs only where needed:

```bash
.venv/bin/pip install -e '.[providers]'
```

Live tests are disabled unless explicitly requested. Configure the matching API
key and `KISANPATH_<PROVIDER>_TEST_MODEL`, then run:

```bash
KISANPATH_RUN_LIVE_LLM_TESTS=1 .venv/bin/pytest -m live
```

Without the opt-in flag, every live case skips cleanly. The shared mocked contract
suite requires no provider credentials or SDK installations.
