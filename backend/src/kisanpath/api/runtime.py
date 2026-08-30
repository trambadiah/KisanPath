"""Dependency health and graceful-drain state owned by the API process."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Protocol


class Dependency(Protocol):
    name: str

    async def check(self) -> None: ...
    async def close(self) -> None: ...


@dataclass
class RuntimeState:
    dependencies: tuple[Dependency, ...] = ()
    accepting_requests: bool = False
    readiness: dict[str, bool] = field(default_factory=dict)
    inflight: int = 0
    _condition: asyncio.Condition = field(default_factory=asyncio.Condition)

    async def enter_request(self) -> bool:
        async with self._condition:
            if not self.accepting_requests:
                return False
            self.inflight += 1
            return True

    async def leave_request(self) -> None:
        async with self._condition:
            self.inflight = max(0, self.inflight - 1)
            self._condition.notify_all()

    async def drain(self, timeout_seconds: float) -> bool:
        self.accepting_requests = False
        try:
            async with asyncio.timeout(timeout_seconds):
                async with self._condition:
                    await self._condition.wait_for(lambda: self.inflight == 0)
            return True
        except TimeoutError:
            return False

    async def check_dependencies(self, timeout_seconds: float) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for dependency in self.dependencies:
            try:
                async with asyncio.timeout(timeout_seconds):
                    await dependency.check()
                results[dependency.name] = True
            except Exception:
                results[dependency.name] = False
        self.readiness = results
        return results

    @property
    def ready(self) -> bool:
        return self.accepting_requests and all(self.readiness.values())
