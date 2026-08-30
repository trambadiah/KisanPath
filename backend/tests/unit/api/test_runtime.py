from __future__ import annotations

import asyncio

from kisanpath.api.runtime import RuntimeState


class Dependency:
    def __init__(self, name: str, *, healthy: bool = True) -> None:
        self.name = name
        self.healthy = healthy
        self.closed = False

    async def check(self) -> None:
        if not self.healthy:
            raise RuntimeError("synthetic outage")

    async def close(self) -> None:
        self.closed = True


async def test_readiness_reports_named_dependencies_without_error_details() -> None:
    state = RuntimeState(dependencies=(Dependency("database"), Dependency("redis", healthy=False)))
    state.accepting_requests = True

    result = await state.check_dependencies(0.1)

    assert result == {"database": True, "redis": False}
    assert not state.ready


async def test_graceful_drain_waits_for_inflight_work() -> None:
    state = RuntimeState()
    state.accepting_requests = True
    assert await state.enter_request()
    drain = asyncio.create_task(state.drain(1))
    await asyncio.sleep(0)
    assert not state.accepting_requests

    await state.leave_request()

    assert await drain
    assert state.inflight == 0
