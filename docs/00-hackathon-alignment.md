# Hackathon Alignment

KisanPath is intentionally designed around the hackathon's required story:

## User and bottleneck

The target user is an Indian farmer who wants to understand which government agriculture schemes may apply to their situation. The bottleneck is fragmented information, complex eligibility language, varying document requirements, multilingual access, and the difficulty of knowing which facts are still missing.

## Purposeful agent use

LLM-backed components are limited to tasks where language understanding helps:

- profile extraction from natural multilingual conversation;
- semantic interpretation of complex non-structurable rules;
- evidence verification when matching natural-language claims;
- localized response composition.

Structured rule evaluation, state transitions, data validation, unit normalization, provenance enforcement, and eligibility aggregation are deterministic services.

## Baseline

The baseline is a single general-purpose LLM prompt using the same frozen scheme material and the same evaluation cases. It does not use the final rule engine, dedicated verifier, or stateful clarification workflow.

## Improvement evidence

Every meaningful iteration is evaluated on the same frozen cases where feasible. The primary metric is eligibility classification accuracy, with false eligibility rate as a prominent safety metric.

## Reproducibility

The judging mode uses:

- frozen reviewed scheme data;
- frozen synthetic farmer cases;
- explicit provider/model configuration;
- exact setup/run/evaluation commands;
- recorded prompt versions;
- machine-readable evaluation outputs;
- representative sanitized trajectories.

## Required submission artifacts mapped to repository

- complete code: repository root/backend/frontend;
- improvement changelog: `docs/14-improvement-changelog-template.md`;
- reproduction guide: `docs/15-reproduction-guide-template.md`;
- solution video plan: `docs/16-demo-video-plan.md`;
- agent trajectories: `trajectories/` plus trajectory schema in `docs/10-agent-trajectories.md`.
