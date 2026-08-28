# Codex Prompt - Domain and Evaluation

Read AGENTS.md, docs/05-domain-model.md, and docs/09-evaluation-plan.md.

Implement the canonical domain layer and frozen evaluation-case schema required by TASKS.md. Add seed synthetic cases covering likely eligible, not eligible, insufficient information, manual review, ambiguous land unit, and multilingual input.

Do not use real farmer PII. Do not implement final scheme logic by hardcoding test answers into application code.

Add strong deterministic unit tests and a small evaluation runner interface that can later execute baseline and final workflows against the same cases.
