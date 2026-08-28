# Agent Trajectory Format

Representative trajectories are required for every LLM-backed agent used in the submission.

## Principles

- trajectories must be easy to follow;
- do not expose hidden chain-of-thought;
- show instructions/version, inputs, structured outputs, tool interactions, validation feedback, retries, and human checkpoints;
- redact secrets and private data;
- use synthetic farmer cases.

## Suggested JSON structure

```json
{
  "trajectory_id": "...",
  "case_id": "...",
  "agent": "profile_agent",
  "prompt_id": "profile.extract",
  "prompt_version": "v3",
  "provider": "...",
  "model": "...",
  "input_summary": {},
  "events": [
    {
      "type": "llm.request",
      "payload_summary": {}
    },
    {
      "type": "llm.response",
      "structured_output": {}
    },
    {
      "type": "validation.feedback",
      "status": "passed"
    }
  ],
  "final_output": {}
}
```

## What to demonstrate

Choose trajectories that reveal useful behavior:

- successful multilingual profile extraction;
- clarification due to missing location;
- critical voice-value confirmation;
- deterministic eligibility failure;
- semantic rule routed to manual review;
- verifier removing an unsupported claim;
- provider retry/fallback in a non-evaluation demo if enabled.
