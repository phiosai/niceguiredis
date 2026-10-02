from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import httpx

from core.pools import PostgresPool, RedisPool

logger = logging.getLogger(__name__)

METRICS_CHANNEL = "metrics:updates"

SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_logs (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    value      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


@dataclass
class Services:
    """Process-wide services shared by every page and client."""

    redis: RedisPool
    postgres: PostgresPool
    api_client: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient(timeout=10.0))

    async def initialize(self) -> None:
        """Connect eagerly so problems show up in the logs at startup.

        Failures are logged rather than raised so the UI still starts; pools retry lazily on next use.
        """
        try:
            await self.redis.initialize()
        except Exception as e:
            logger.error("Redis unavailable at startup (%s): %s", self.redis.url, e)
        try:
            await self.postgres.initialize()
            await self.postgres.execute(SCHEMA)
        except Exception as e:
            logger.error("Postgres unavailable at startup: %s", e)

    async def close(self) -> None:
        for name, closer in (
            ("redis", self.redis.close),
            ("postgres", self.postgres.close),
            ("api_client", self.api_client.aclose),
        ):
            try:
                await closer()
            except Exception:
                logger.exception("Error closing %s", name)


def create_services() -> Services:
    return Services(
        redis=RedisPool(url=os.getenv("REDIS_URL", "redis://localhost:6379/0")),
        postgres=PostgresPool(dsn=os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dbname")),
    )
