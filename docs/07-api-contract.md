# API Contract Outline

Use versioned REST endpoints plus SSE or WebSocket for progressive conversation events if needed.

## Public endpoints

### `POST /v1/conversations`
Create a session.

Input may include preferred language and client capabilities.

### `POST /v1/conversations/{id}/messages`
Submit typed input.

Returns workflow result or an accepted/stream token depending on implementation.

### `POST /v1/conversations/{id}/audio`
Submit push-to-talk audio. Response includes transcript and workflow progress.

### `GET /v1/conversations/{id}`
Read safe canonical session state and final recommendations.

### `GET /v1/schemes/{id}`
Read user-safe scheme detail, evidence summary, documents, and reviewed official sources.

### `POST /v1/eligibility/evaluate`
Developer/judge endpoint for structured evaluation without conversational UX.

### `GET /v1/health`
Liveness only.

### `GET /v1/readiness`
Dependency/config readiness without leaking secrets.

## Progressive event types

```text
transcript.ready
profile.updated
confirmation.required
clarification.required
discovery.started
discovery.completed
eligibility.completed
verification.completed
response.ready
audio.ready
workflow.failed
```

Events may explain high-level progress but must not contain hidden chain-of-thought.

## Error envelope

Use a stable internal shape such as:

```json
{
  "error": {
    "code": "LLM_UNAVAILABLE",
    "message": "The assistant is temporarily unavailable.",
    "retryable": true,
    "request_id": "..."
  }
}
```

Never return raw provider exceptions, database messages, stack traces, or secrets to clients.

## Application workflow boundary

The transport-neutral command/result models for typed messages are implemented in
`backend/src/kisanpath/workflows/models.py`. `TextWorkflowResult` returns safe
canonical conversation state, a localized response or pending question, and the
progressive events listed above. It does not expose provider responses or hidden
reasoning.

The current phase implements the application boundary, not FastAPI routes. A later
transport layer can map `POST /v1/conversations`, message submission, and session
reads directly onto `TextEligibilityWorkflow` and `ConversationRepository` without
moving business logic into route handlers.
