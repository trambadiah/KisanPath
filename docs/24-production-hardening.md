# Production Hardening Boundaries

This phase adds production-shaped controls without changing farmer-profile,
retrieval, eligibility, evidence-verification, or localization semantics. It is an
implementation boundary and reproducible deployment path—not a claim that the
current repository is production-certified.

## Runtime path

The FastAPI shell is `backend/src/kisanpath/api/app.py`. It currently exposes:

- `GET /v1/health`: process liveness only;
- `GET /v1/readiness`: dependency and migration readiness, with no connection details;
- `GET /v1/admin/status`: authenticated auditor/operator runtime status;
- `GET /internal/metrics`: operator-only Prometheus text exposition.

The public conversation and scheme routes described in `docs/07-api-contract.md`
are still application contracts, not mounted FastAPI endpoints. Docker therefore
leaves `NEXT_PUBLIC_KISANPATH_API_URL` empty by default so the reviewed synthetic UI
adapter remains usable. Set it only after those transport routes are implemented.

## Request security

- `X-Request-ID` is accepted only when it matches a bounded safe character set;
  otherwise the server creates a UUID. It is returned on responses.
- JSON and audio request limits are independent. Both declared `Content-Length` and
  streamed body bytes are checked.
- Audio paths accept only `audio/*` or `multipart/form-data` media types.
- Public and admin rate limits are separate. Docker uses the atomic Redis adapter;
  dependency-injected local/test apps can use the bounded single-process adapter.
- Wildcard CORS is rejected by configuration. Security and no-store headers are
  applied at the API boundary.
- API errors use the stable KisanPath envelope and never return provider/database
  exception text.

Defaults and environment names are documented in `.env.example`.

## Admin authentication and RBAC

`KISANPATH_ADMIN_TOKENS_JSON` is a runtime-secret JSON array of opaque tokens,
subjects, and roles. Tokens are hashed immediately for comparison and are never
returned. With no configured tokens, all admin authentication fails closed.

The reusable policy maps actions explicitly:

| Action | Required role |
|---|---|
| view audit events | `auditor` |
| review extracted corpus records | `reviewer` |
| publish or retire corpus versions | `publisher` |
| inspect/operate runtime controls | `operator` |

An operator is not implicitly a publisher. Future mutation routes must invoke
`AdminAuthenticator.authorize_action` before calling ingestion publication units of
work and must write an `AuditEvent` through the `AuditSink` port.

## Provider retry and fallback policy

The `LLMRouter` retries only normalized timeout, rate-limit, and unavailable errors.
Authentication, capability, invalid-response, and schema-validation failures are
not retried or hidden by fallback.

- Attempts and exponential delays are bounded by typed configuration.
- A provider `Retry-After` value is honored only up to the configured maximum.
- Fallback occurs only after the primary provider's retry budget is exhausted.
- Streaming retries/fallback are allowed only before the first event is emitted.
- Cancellation is not swallowed.
- Evaluation fallback remains separately controlled by
  `LLM_EVALUATION_FALLBACK_ENABLED` and defaults off.

Mocked outage tests run without credentials. Live provider tests remain explicit
opt-in checks and do not constitute an availability benchmark.

## Evidence and prompt injection

Published status remains the trust gate for eligibility-visible scheme records,
but published text is still treated as untrusted prompt data. Retrieved excerpts:

1. have control characters removed and length bounded;
2. are tagged with source and locator metadata;
3. flag common instruction-like markers for audit;
4. are enclosed in `UNTRUSTED_EVIDENCE_DATA` delimiters;
5. are accompanied by a system instruction that forbids executing embedded
   commands, role changes, or tool requests.

Flags do not alter eligibility by themselves. Prompt-injection defenses reduce
risk; they cannot prove that arbitrary model behavior is safe. Deterministic rule
evaluation and local schema/provenance checks remain the controlling safeguards.

## Logs, metrics, and traces

Production JSON logs include event name, safe bounded metadata, and any active
correlation identifiers. Authorization, cookies, credentials, likely API-key
fields, Aadhaar-like identifiers, and binary bodies are redacted. Request bodies,
raw audio, and hidden reasoning are not logged.

Context variables exist for `request_id`, `conversation_id`, `workflow_run_id`,
`llm_run_id`, `tool_run_id`, and `evaluation_run_id`. The HTTP and LLM boundaries
currently bind the applicable IDs. Workflow transition, retrieval, HTTP, retry,
fallback, latency, and candidate-count metric ports are implemented with bounded
labels. The tracing port is compatible with an OpenTelemetry adapter, but no trace
exporter is configured in this phase.

`InMemoryMetrics` is suitable for one-process development and scraping demos. It is
not durable and does not aggregate replicas. A production deployment must replace
or scrape it and attach an OpenTelemetry SDK/exporter at the provided `Tracer` port.

## Database migrations and lifecycle

Alembic revision `20260829_0001` creates the initial conversation, source,
ingestion, published-version/chunk, and audit-event tables. Migrations are explicit:
API startup never runs DDL. Readiness requires both `SELECT 1` and the expected
`alembic_version` value.

At shutdown the service stops accepting normal work, waits up to the configured
grace period for in-flight requests, and then closes database/Redis resources.
Liveness stays available during drain while readiness returns not-ready.

The existing production repositories are still storage-neutral/in-memory; the
migration is a database boundary for the future PostgreSQL repository adapters. No
claim is made that workflow state is durable in the current API shell.

## Reproducible Docker path

From a clean checkout with Docker Compose v2:

```bash
cp .env.example .env
docker compose config
docker compose build
docker compose up
```

Compose waits for PostgreSQL, runs `alembic upgrade head` once, then starts the API,
Redis-backed request limiting, and standalone Next.js frontend. Optional Ollama is
isolated behind a profile:

```bash
docker compose --profile local-llm up
```

Verification endpoints:

```bash
curl -i http://localhost:8000/v1/health
curl -i http://localhost:8000/v1/readiness
curl -i http://localhost:3000
```

Do not place real secrets in `.env` for a shared environment. Inject them through
the deployment platform's secret manager. Terminate TLS and configure trusted proxy
addresses at ingress; the local Compose path is intentionally plain HTTP.

## Backup and restore boundary

PostgreSQL backups must include schema and data, be encrypted outside the database,
have retention/access controls, and be restored periodically into an isolated
database. A candidate procedure uses `pg_dump --format=custom`, restores with
`pg_restore` into a new database, then verifies the Alembic revision, publication
counts, source hashes, and representative read-only queries before declaring the
exercise successful. Object-store source snapshots require independent versioning
and retention.

This repository does not run or certify a backup/restore exercise, does not ship an
object-store adapter, and does not define organization-specific RPO/RTO values.

## Load scaffold and explicit limitations

`load/locustfile.py` exercises health, readiness, request guards, and optional admin
authentication. No result is checked in and no throughput, latency, availability,
cost, or production-readiness claim is made.

Remaining limitations include:

- conversation/scheme/evaluation FastAPI routes are not mounted;
- PostgreSQL repository implementations are not yet connected to workflows;
- metrics and tracing have ports but no managed backend/dashboard/exporter;
- admin mutation/audit routes are not implemented;
- CSRF protection is not applicable to the current bearer-token API, but must be
  designed if cookie sessions are introduced;
- ingress TLS, WAF, secret-manager integration, key rotation, cloud IAM, IaC,
  vulnerability scanning, backups, and disaster-recovery exercises are deployment
  responsibilities not implemented here;
- the load scaffold and mocked outage tests are engineering checks, not production
  performance or reliability evidence.
