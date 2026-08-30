"""Audit-event port for privileged and security-relevant mutations."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    occurred_at: datetime
    actor_id: str = Field(min_length=1)
    action: str = Field(min_length=1, max_length=200)
    target_type: str = Field(min_length=1, max_length=100)
    target_id: str = Field(min_length=1, max_length=300)
    request_id: str | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AuditSink(Protocol):
    async def record(self, event: AuditEvent) -> None: ...
