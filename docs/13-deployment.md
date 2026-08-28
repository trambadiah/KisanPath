# Deployment Plan

## Local / judge mode

Use Docker Compose for reproducibility:

```text
frontend
backend API
worker (when needed)
PostgreSQL
Redis
optional Ollama profile
```

The judge path should not require production infrastructure.

## Production topology

```text
CDN/static hosting
        |
        v
Load balancer / ingress
        |
        v
API containers -------- Worker containers
        |                      |
        +-----------+----------+
                    |
          PostgreSQL / Redis / Object Store
                    |
          External/local AI providers
```

## Production principles

- stateless API containers;
- migrations run explicitly, not implicitly at every startup;
- health vs readiness endpoints separated;
- graceful shutdown for streaming calls;
- retry only idempotent/safe operations;
- queue long-running ingestion/evaluation jobs;
- provider credentials from secret manager;
- backups and restore procedures documented;
- object storage versioning for important source snapshots where appropriate.

## Infrastructure as code

Add cloud-specific IaC only after the local architecture and runtime boundaries stabilize. Keep application configuration cloud-neutral.
