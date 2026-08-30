"""Validated, cloud-neutral runtime settings loaded from environment."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuntimeSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    environment: str = Field(default="development", min_length=1)
    log_level: str = "INFO"
    json_logs: bool = True
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    public_rate_limit_per_minute: int = Field(default=60, ge=1, le=100_000)
    admin_rate_limit_per_minute: int = Field(default=20, ge=1, le=10_000)
    max_json_bytes: int = Field(default=1_000_000, ge=1024, le=20_000_000)
    max_audio_bytes: int = Field(default=15_000_000, ge=1024, le=100_000_000)
    shutdown_grace_seconds: float = Field(default=15, ge=0, le=120)
    dependency_timeout_seconds: float = Field(default=2, gt=0, le=30)
    database_url: str | None = None
    redis_url: str | None = None
    admin_tokens_json: str | None = None

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_cors(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if "*" in value:
            raise ValueError("wildcard CORS origins are forbidden")
        if any(urlparse(origin).scheme not in {"http", "https"} for origin in value):
            raise ValueError("CORS origins must be absolute HTTP(S) origins")
        return value


def _boolean(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def load_runtime_settings(environ: Mapping[str, str] | None = None) -> RuntimeSettings:
    env = os.environ if environ is None else environ
    origins_raw = env.get("KISANPATH_CORS_ORIGINS", '["http://localhost:3000"]')
    try:
        decoded_origins = json.loads(origins_raw)
        if not isinstance(decoded_origins, list) or not all(
            isinstance(origin, str) for origin in decoded_origins
        ):
            raise TypeError
        origins = tuple(decoded_origins)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("KISANPATH_CORS_ORIGINS must be a JSON array") from exc
    return RuntimeSettings(
        environment=env.get("APP_ENV", "development"),
        log_level=env.get("APP_LOG_LEVEL", "INFO"),
        json_logs=_boolean(env.get("KISANPATH_JSON_LOGS"), True),
        cors_origins=origins,
        public_rate_limit_per_minute=int(env.get("KISANPATH_PUBLIC_RATE_LIMIT", "60")),
        admin_rate_limit_per_minute=int(env.get("KISANPATH_ADMIN_RATE_LIMIT", "20")),
        max_json_bytes=int(env.get("KISANPATH_MAX_JSON_BYTES", "1000000")),
        max_audio_bytes=int(env.get("KISANPATH_MAX_AUDIO_BYTES", "15000000")),
        shutdown_grace_seconds=float(env.get("KISANPATH_SHUTDOWN_GRACE_SECONDS", "15")),
        dependency_timeout_seconds=float(env.get("KISANPATH_DEPENDENCY_TIMEOUT_SECONDS", "2")),
        database_url=env.get("DATABASE_URL") or None,
        redis_url=env.get("REDIS_URL") or None,
        admin_tokens_json=env.get("KISANPATH_ADMIN_TOKENS_JSON") or None,
    )
