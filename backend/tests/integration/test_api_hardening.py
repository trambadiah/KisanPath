from __future__ import annotations

import json

import httpx
from asgi_lifespan import LifespanManager

from kisanpath.api.app import create_app
from kisanpath.api.config import RuntimeSettings


def settings(**updates: object) -> RuntimeSettings:
    tokens = json.dumps(
        [
            {
                "token": "synthetic-operator-token-0001",
                "subject": "synthetic-operator",
                "roles": ["operator", "auditor"],
            },
            {
                "token": "synthetic-publisher-token-001",
                "subject": "synthetic-publisher",
                "roles": ["publisher"],
            },
        ]
    )
    values: dict[str, object] = {
        "json_logs": False,
        "admin_tokens_json": tokens,
        "public_rate_limit_per_minute": 100,
        "admin_rate_limit_per_minute": 100,
        "max_json_bytes": 1024,
    }
    values.update(updates)
    return RuntimeSettings.model_validate(values)


async def client_for(app: object):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_health_readiness_correlation_and_security_headers() -> None:
    app = create_app(settings=settings(), dependencies=())
    async with LifespanManager(app):
        async with await client_for(app) as client:
            health = await client.get("/v1/health", headers={"X-Request-ID": "request-test-0001"})
            readiness = await client.get("/v1/readiness")

    assert health.status_code == 200
    assert health.headers["x-request-id"] == "request-test-0001"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready", "dependencies": {}}


async def test_admin_boundary_distinguishes_authentication_and_authorization() -> None:
    app = create_app(settings=settings(), dependencies=())
    async with LifespanManager(app):
        async with await client_for(app) as client:
            unauthenticated = await client.get("/v1/admin/status")
            unauthorized = await client.get(
                "/v1/admin/status",
                headers={"Authorization": "Bearer synthetic-publisher-token-001"},
            )
            authorized = await client.get(
                "/v1/admin/status",
                headers={"Authorization": "Bearer synthetic-operator-token-0001"},
            )

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "UNAUTHENTICATED"
    assert unauthorized.status_code == 403
    assert unauthorized.json()["error"]["code"] == "FORBIDDEN"
    assert authorized.status_code == 200
    assert authorized.json()["actor"] == "synthetic-operator"


async def test_declared_and_streamed_payload_limits_reject_before_business_logic() -> None:
    app = create_app(settings=settings(), dependencies=())
    async with LifespanManager(app):
        async with await client_for(app) as client:
            response = await client.post(
                "/v1/unknown",
                content="x" * 2048,
                headers={"Content-Type": "application/json"},
            )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


async def test_rate_limit_returns_stable_safe_error_envelope() -> None:
    limited = settings(public_rate_limit_per_minute=2)
    app = create_app(settings=limited, dependencies=())
    async with LifespanManager(app):
        async with await client_for(app) as client:
            await client.get("/v1/not-a-route")
            await client.get("/v1/not-a-route")
            response = await client.get("/v1/not-a-route")

    assert response.status_code == 429
    assert response.headers["retry-after"]
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert "request_id" in response.json()["error"]
