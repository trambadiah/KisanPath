# Codex Prompt - Farmer Workflow

Read AGENTS.md, docs/04-agent-workflow.md, docs/05-domain-model.md, and docs/07-api-contract.md.

Implement the first complete text-based vertical slice:

farmer text -> profile extraction -> profile merge -> clarification/confirmation -> candidate scheme retrieval -> deterministic eligibility -> semantic fallback only when explicitly required -> evidence verification -> localized response.

Use the explicit workflow state machine. Persist canonical state. Never use LLM chat history as the only memory.

Add an end-to-end test where missing information causes clarification instead of a guessed decision, and another where a deterministic FAIL cannot be overridden by an LLM-backed component.
