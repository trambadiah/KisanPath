"""Production-shaped API shell with explicit startup/readiness/shutdown behavior."""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kisanpath.api.config import RuntimeSettings, load_runtime_settings
from kisanpath.api.middleware import HardeningMiddleware
from kisanpath.api.rate_limit import InMemoryRateLimiter, RateLimiter, RedisRateLimiter
from kisanpath.api.runtime import Dependency, RuntimeState
from kisanpath.observability.context import request_id_var
from kisanpath.observability.logging import configure_logging
from kisanpath.observability.metrics import InMemoryMetrics
from kisanpath.persistence.database import DatabaseDependency, RedisDependency
from kisanpath.security.auth import (
    AdminAuthenticationError,
    AdminAuthenticator,
    AdminAuthorizationError,
    AdminPrincipal,
    AdminRole,
)

bearer = HTTPBearer(auto_error=False)


def create_app(
    *,
    settings: RuntimeSettings | None = None,
    dependencies: tuple[Dependency, ...] | None = None,
    limiter: RateLimiter | None = None,
) -> FastAPI:
    config = settings or load_runtime_settings()
    configure_logging(level=config.log_level, json_logs=config.json_logs)
    logger = logging.getLogger("kisanpath.lifecycle")
    resolved_dependencies: list[Dependency] = list(dependencies or ())
    redis_dependency: RedisDependency | None = None
    if dependencies is None:
        if config.database_url:
            resolved_dependencies.append(DatabaseDependency(config.database_url))
        if config.redis_url:
            redis_dependency = RedisDependency(config.redis_url)
            resolved_dependencies.append(redis_dependency)
    resolved_limiter = limiter or (
        RedisRateLimiter(redis_dependency.client) if redis_dependency else InMemoryRateLimiter()
    )
    runtime = RuntimeState(dependencies=tuple(resolved_dependencies))
    metrics = InMemoryMetrics()
    authenticator = AdminAuthenticator.from_json(config.admin_tokens_json)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        runtime.accepting_requests = True
        readiness = await runtime.check_dependencies(config.dependency_timeout_seconds)
        logger.info(
            "service.started", extra={"environment": config.environment, "dependencies": readiness}
        )
        try:
            yield
        finally:
            drained = await runtime.drain(config.shutdown_grace_seconds)
            await asyncio.gather(
                *(dependency.close() for dependency in runtime.dependencies), return_exceptions=True
            )
            if redis_dependency is None:
                await resolved_limiter.close()
            logger.info("service.stopped", extra={"graceful_drain_completed": drained})

    app = FastAPI(
        title="KisanPath API",
        version="1.0.0",
        docs_url=None if config.environment == "production" else "/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.runtime = runtime
    app.state.metrics = metrics
    app.state.settings = config
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(
        HardeningMiddleware,
        settings=config,
        runtime=runtime,
        limiter=resolved_limiter,
        metrics=metrics,
    )

    async def admin_principal(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> AdminPrincipal:
        authorization = f"Bearer {credentials.credentials}" if credentials else None
        try:
            return authenticator.authenticate(authorization)
        except AdminAuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Administrator authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    def require_any_role(
        *roles: AdminRole,
    ) -> Callable[[AdminPrincipal], Awaitable[AdminPrincipal]]:
        async def dependency(
            principal: Annotated[AdminPrincipal, Depends(admin_principal)],
        ) -> AdminPrincipal:
            try:
                authenticator.authorize_any(principal, frozenset(roles))
                return principal
            except AdminAuthorizationError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Administrator role is not authorized",
                ) from exc

        return dependency

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        request_id = request_id_var.get() or "unknown"
        code = {401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND"}.get(
            exc.status_code, "REQUEST_REJECTED"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": str(exc.detail),
                    "retryable": False,
                    "request_id": request_id,
                }
            },
            headers=exc.headers,
        )

    @app.get("/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/v1/readiness")
    async def readiness() -> JSONResponse:
        checks = await runtime.check_dependencies(config.dependency_timeout_seconds)
        ready = runtime.ready
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"status": "ready" if ready else "not_ready", "dependencies": checks},
        )

    @app.get("/v1/admin/status")
    async def admin_status(
        principal: Annotated[
            AdminPrincipal, Depends(require_any_role(AdminRole.AUDITOR, AdminRole.OPERATOR))
        ],
    ) -> dict[str, object]:
        return {
            "environment": config.environment,
            "actor": principal.subject,
            "roles": sorted(role.value for role in principal.roles),
            "ready": runtime.ready,
            "dependencies": runtime.readiness,
        }

    @app.get("/internal/metrics", response_class=PlainTextResponse)
    async def prometheus_metrics(
        _principal: Annotated[AdminPrincipal, Depends(require_any_role(AdminRole.OPERATOR))],
    ) -> str:
        return metrics.render_prometheus()

    return app


app = create_app()
