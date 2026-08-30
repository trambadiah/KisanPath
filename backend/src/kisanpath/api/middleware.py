"""ASGI request guards: correlation, limits, rate limiting, logging, and drain tracking."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from kisanpath.api.config import RuntimeSettings
from kisanpath.api.rate_limit import RateLimiter
from kisanpath.api.runtime import RuntimeState
from kisanpath.observability.context import bind_context
from kisanpath.observability.metrics import MetricsSink

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_CONVERSATION_PATH = re.compile(r"^/v1/conversations/([^/]+)")
_DYNAMIC_SEGMENT = re.compile(r"/[0-9a-fA-F-]{16,}(?=/|$)")
_RESOURCE_ID = re.compile(r"^(/v1/(?:conversations|schemes))/[^/]+")
_EXEMPT_PATHS = {"/v1/health", "/v1/readiness"}


class PayloadTooLargeError(Exception):
    pass


class HardeningMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: RuntimeSettings,
        runtime: RuntimeState,
        limiter: RateLimiter,
        metrics: MetricsSink,
    ) -> None:
        self.app = app
        self.settings = settings
        self.runtime = runtime
        self.limiter = limiter
        self.metrics = metrics
        self.logger = logging.getLogger("kisanpath.api")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path", ""))
        headers = {
            key.decode("latin1").lower(): value.decode("latin1")
            for key, value in scope.get("headers", [])
        }
        supplied_id = headers.get("x-request-id")
        request_id = (
            supplied_id if supplied_id and _REQUEST_ID.fullmatch(supplied_id) else str(uuid4())
        )
        conversation_match = _CONVERSATION_PATH.match(path)
        tokens = bind_context(
            request_id=request_id,
            conversation_id=conversation_match.group(1)[:200] if conversation_match else None,
        )
        started = time.perf_counter()
        entered = False
        status_code = 500
        response_started = False
        try:
            if path not in _EXEMPT_PATHS:
                entered = await self.runtime.enter_request()
                if not entered:
                    status_code = 503
                    await self._error(
                        send,
                        503,
                        "SERVICE_DRAINING",
                        "The service is not accepting new work.",
                        request_id,
                        retryable=True,
                    )
                    return
            payload_limit = (
                self.settings.max_audio_bytes
                if path.endswith("/audio")
                else self.settings.max_json_bytes
            )
            content_length = headers.get("content-length")
            try:
                declared_length = int(content_length) if content_length else 0
            except ValueError:
                declared_length = -1
            if declared_length < 0:
                status_code = 400
                await self._error(
                    send,
                    400,
                    "INVALID_CONTENT_LENGTH",
                    "The request content length is invalid.",
                    request_id,
                )
                return
            if declared_length > payload_limit:
                status_code = 413
                await self._error(
                    send,
                    413,
                    "PAYLOAD_TOO_LARGE",
                    "The request payload exceeds the configured limit.",
                    request_id,
                )
                return
            if path.endswith("/audio") and scope.get("method") == "POST":
                content_type = headers.get("content-type", "").casefold()
                if not (
                    content_type.startswith("audio/")
                    or content_type.startswith("multipart/form-data")
                ):
                    status_code = 415
                    await self._error(
                        send,
                        415,
                        "UNSUPPORTED_MEDIA_TYPE",
                        "Audio input must use an approved audio or multipart media type.",
                        request_id,
                    )
                    return
            if path not in _EXEMPT_PATHS:
                limit = (
                    self.settings.admin_rate_limit_per_minute
                    if path.startswith("/v1/admin") or path.startswith("/internal")
                    else self.settings.public_rate_limit_per_minute
                )
                identity = headers.get("authorization") or str(
                    (scope.get("client") or ("unknown", 0))[0]
                )
                key = hashlib.sha256(f"{path.split('/')[1:3]}:{identity}".encode()).hexdigest()
                decision = await self.limiter.check(key, limit=limit, window_seconds=60)
                if not decision.allowed:
                    status_code = 429
                    await self._error(
                        send,
                        429,
                        "RATE_LIMITED",
                        "Too many requests. Retry after the indicated delay.",
                        request_id,
                        retryable=True,
                        extra_headers=[
                            (b"retry-after", str(decision.retry_after_seconds).encode())
                        ],
                    )
                    return

            received = 0

            async def limited_receive() -> Message:
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > payload_limit:
                        raise PayloadTooLargeError
                return message

            async def guarded_send(message: Message) -> None:
                nonlocal status_code, response_started
                if message["type"] == "http.response.start":
                    response_started = True
                    status_code = int(message["status"])
                    outgoing = list(message.get("headers", []))
                    outgoing.extend(
                        [
                            (b"x-request-id", request_id.encode()),
                            (b"x-content-type-options", b"nosniff"),
                            (b"x-frame-options", b"DENY"),
                            (b"referrer-policy", b"no-referrer"),
                            (b"permissions-policy", b"camera=(), geolocation=(), payment=()"),
                            (b"cache-control", b"no-store"),
                        ]
                    )
                    message = {**message, "headers": outgoing}
                await send(message)

            try:
                await self.app(scope, limited_receive, guarded_send)
            except PayloadTooLargeError:
                if not response_started:
                    await self._error(
                        send,
                        413,
                        "PAYLOAD_TOO_LARGE",
                        "The request payload exceeds the configured limit.",
                        request_id,
                    )
                    status_code = 413
                else:
                    raise
        finally:
            if entered:
                await self.runtime.leave_request()
            route = _RESOURCE_ID.sub(r"\1/{id}", path)
            route = _DYNAMIC_SEGMENT.sub("/{id}", route)[:200]
            duration_ms = (time.perf_counter() - started) * 1000
            self.metrics.increment(
                "kisanpath_api_requests_total",
                labels={
                    "method": str(scope.get("method", "")),
                    "route": route,
                    "status": str(status_code),
                },
            )
            self.metrics.observe(
                "kisanpath_api_request_duration_ms",
                duration_ms,
                labels={"method": str(scope.get("method", "")), "route": route},
            )
            self.logger.info(
                "api.request.completed",
                extra={
                    "method": scope.get("method"),
                    "route": route,
                    "status": status_code,
                    "duration_ms": round(duration_ms, 3),
                },
            )
            tokens.reset()

    @staticmethod
    async def _error(
        send: Send,
        status: int,
        code: str,
        message: str,
        request_id: str,
        *,
        retryable: bool = False,
        extra_headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        body = json.dumps(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "retryable": retryable,
                    "request_id": request_id,
                }
            },
            separators=(",", ":"),
        ).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"x-request-id", request_id.encode()),
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"referrer-policy", b"no-referrer"),
            (b"cache-control", b"no-store"),
            *(extra_headers or []),
        ]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})
