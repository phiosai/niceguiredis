from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
from typing import Any, Awaitable, Callable, Optional

import asyncpg
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.client import PubSub

logger = logging.getLogger(__name__)

MessageCallback = Callable[[str], Any]
Unsubscribe = Callable[[], Awaitable[None]]


class RedisPool:
    """Shared Redis connection pool with a single fan-out pub/sub listener.

    One background task holds one pub/sub connection for the whole process; any number
    of callbacks (e.g. one per browser tab) can be attached to a channel.
    """

    def __init__(self, url: str, max_connections: int = 50) -> None:
        self.url = url
        self.max_connections = max_connections
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Redis] = None
        self._pubsub: Optional[PubSub] = None
        self._subscribers: dict[str, list[MessageCallback]] = {}
        self._has_channels = asyncio.Event()
        self._listener_task: Optional[asyncio.Task] = None
        self._listening = False

    @property
    def is_listening(self) -> bool:
        return self._listening

    async def initialize(self) -> None:
        if self.pool is None:
            self.pool = ConnectionPool.from_url(
                self.url, max_connections=self.max_connections, decode_responses=True
            )
            self.client = Redis(connection_pool=self.pool)
            logger.info("Redis pool created for %s", self.url)
        assert self.client is not None
        await self.client.ping()

    async def get_client(self) -> Redis:
        if self.client is None:
            await self.initialize()
        assert self.client is not None
        return self.client

    async def get(self, key: str) -> Optional[str]:
        return await (await self.get_client()).get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        return bool(await (await self.get_client()).set(key, value, ex=ex))

    async def dbsize(self) -> int:
        return int(await (await self.get_client()).dbsize())

    async def publish(self, channel: str, message: str) -> int:
        return int(await (await self.get_client()).publish(channel, message))

    async def subscribe(self, channel: str, callback: MessageCallback) -> Unsubscribe:
        """Register ``callback`` for ``channel``; returns a coroutine function that unregisters it."""
        is_new = channel not in self._subscribers
        self._subscribers.setdefault(channel, []).append(callback)
        self._has_channels.set()
        if is_new and self._pubsub is not None:
            with contextlib.suppress(Exception):  # listener resubscribes everything on reconnect
                await self._pubsub.subscribe(channel)
        if self._listener_task is None or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._listen(), name="redis-pubsub-listener")

        async def unsubscribe() -> None:
            callbacks = self._subscribers.get(channel, [])
            if callback in callbacks:
                callbacks.remove(callback)
            if not callbacks and channel in self._subscribers:
                del self._subscribers[channel]
                if self._pubsub is not None:
                    with contextlib.suppress(Exception):
                        await self._pubsub.unsubscribe(channel)

        return unsubscribe

    async def _dispatch(self, channel: str, data: str) -> None:
        for callback in list(self._subscribers.get(channel, [])):
            try:
                result = callback(data)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Error in pub/sub callback for %s", channel)

    async def _listen(self) -> None:
        """Process-wide listener with reconnect + resubscribe and exponential backoff."""
        backoff = 1.0
        while True:
            pubsub: Optional[PubSub] = None
            try:
                await self._has_channels.wait()
                client = await self.get_client()
                pubsub = client.pubsub(ignore_subscribe_messages=True)
                self._pubsub = pubsub
                await pubsub.subscribe(*self._subscribers.keys())
                self._listening = True
                backoff = 1.0
                logger.info("Pub/sub listening on %s", list(self._subscribers))
                while self._subscribers:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message["type"] == "message":
                        await self._dispatch(message["channel"], message["data"])
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Redis pub/sub error: %s; reconnecting in %.0fs", e, backoff)
                self._listening = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
            finally:
                self._listening = False
                self._pubsub = None
                if pubsub is not None:
                    with contextlib.suppress(Exception):
                        await pubsub.aclose()
                if not self._subscribers:
                    self._has_channels.clear()

    async def close(self) -> None:
        if self._listener_task is not None:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None
        if self.client is not None:
            await self.client.aclose()
            self.client = None
        if self.pool is not None:
            await self.pool.aclose()
            self.pool = None
        logger.info("Redis pool closed")


class PostgresPool:
    """Shared PostgreSQL connection pool (asyncpg)."""

    def __init__(
        self,
        dsn: str,
        min_size: int = 1,
        max_size: int = 10,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0,
    ) -> None:
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.max_queries = max_queries
        self.max_inactive_connection_lifetime = max_inactive_connection_lifetime
        self.pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with self._lock:  # avoid two concurrent callers creating two pools
            if self.pool is None:
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    max_queries=self.max_queries,
                    max_inactive_connection_lifetime=self.max_inactive_connection_lifetime,
                )
                logger.info("Postgres pool initialized: %d-%d connections", self.min_size, self.max_size)

    async def get_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            await self.initialize()
        assert self.pool is not None
        return self.pool

    async def fetch(self, query: str, *args: Any) -> list[dict]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return [dict(row) for row in await conn.fetch(query, *args)]

    async def fetchrow(self, query: str, *args: Any) -> Optional[dict]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetchval(self, query: str, *args: Any) -> Any:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args: list[tuple]) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(query, args)

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
            logger.info("Postgres pool closed")
