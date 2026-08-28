# Codex Prompt - Production Hardening

Read AGENTS.md, docs/11-security-privacy.md, docs/12-observability.md, docs/13-deployment.md, and docs/18-definition-of-done.md.

Harden the current implementation without changing product semantics:
- structured logs and correlation IDs;
- metrics/tracing boundaries;
- safe provider retries/fallback;
- rate and payload limits;
- admin authorization/RBAC boundaries;
- prompt-injection protections around retrieved evidence;
- secret redaction;
- DB migrations and startup/readiness behavior;
- graceful shutdown;
- provider outage tests;
- load-test scaffold;
- reproducible Docker path.

Do not create fake production claims. Document limitations explicitly.
