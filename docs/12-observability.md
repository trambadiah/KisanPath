# Observability

## Correlation identifiers

Propagate at least:

```text
request_id
conversation_id
workflow_run_id
llm_run_id
tool_run_id
evaluation_run_id (when applicable)
```

## Structured logging

Use structured JSON logs in production. Avoid raw `print()` debugging in committed code.

Never log:

- API keys;
- authorization headers;
- unredacted sensitive identity data;
- raw private audio by default;
- hidden chain-of-thought.

## Metrics

### API
- request count/latency/error rate;
- active conversations.

### Workflow
- completion rate;
- clarification count;
- manual-review rate;
- stage latency;
- retries.

### LLM
- provider/model request count;
- latency;
- error/rate-limit count;
- input/output tokens when available;
- estimated cost;
- schema validation failure;
- fallback count.

### Retrieval/eligibility
- retrieval latency;
- candidates returned;
- deterministic vs semantic rules evaluated;
- PASS/FAIL/UNKNOWN/MANUAL_REVIEW distribution;
- unsupported-claim blocks.

### Voice
- transcription latency;
- critical-field low-confidence rate;
- voice retry/cancel rate;
- TTS latency.

## Tracing

Use OpenTelemetry-compatible instrumentation boundaries where feasible. Traces should expose state transitions and external calls without revealing private reasoning.
