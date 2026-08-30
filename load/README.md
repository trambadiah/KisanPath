# Load-test scaffold

This Locust scenario checks liveness, readiness, request guards, and the optional
protected admin boundary. It does **not** establish a production capacity claim and
does not yet exercise the farmer workflow because the FastAPI conversation routes
are not wired in this repository phase.

Run against a disposable environment:

```bash
cd backend
.venv/bin/locust -f ../load/locustfile.py --host http://localhost:8000
```

Record environment, image digest, user count, spawn rate, duration, error rate, and
latency percentiles before interpreting any result. Never put real farmer data or
production admin tokens in a load scenario.
