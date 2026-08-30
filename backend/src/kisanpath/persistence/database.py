"""Async SQL dependency lifecycle; migrations remain an explicit deployment step."""

from __future__ import annotations

from typing import Any


class DatabaseDependency:
    name = "database"
    expected_migration_revision = "20260829_0001"

    def __init__(self, url: str) -> None:
        from sqlalchemy.ext.asyncio import create_async_engine

        self._engine: Any = create_async_engine(url, pool_pre_ping=True)

    async def check(self) -> None:
        from sqlalchemy import text

        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != self.expected_migration_revision:
                raise RuntimeError("database migration revision is not current")

    async def close(self) -> None:
        await self._engine.dispose()


class RedisDependency:
    name = "redis"

    def __init__(self, url: str) -> None:
        from redis.asyncio import from_url

        self.client: Any = from_url(url, decode_responses=True)  # type: ignore[no-untyped-call]

    async def check(self) -> None:
        if not await self.client.ping():
            raise RuntimeError("redis ping failed")

    async def close(self) -> None:
        await self.client.aclose()
