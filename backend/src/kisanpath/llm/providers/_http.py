"""Common async HTTP adapter mechanics for local/compatible endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from kisanpath.llm.config import ProviderSettings


def http_client(
    settings: ProviderSettings,
    *,
    headers: Mapping[str, str] | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=(settings.base_url or "").rstrip("/"),
        headers=dict(headers or {}),
        timeout=settings.timeout_seconds,
    )


def require_object(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("provider response must be a JSON object")
    return payload
