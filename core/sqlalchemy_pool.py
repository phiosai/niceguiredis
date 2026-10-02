"""Alternative to ``PostgresPool`` using SQLAlchemy's async engine (not wired into the app).

The DSN must name an async driver, e.g. ``postgresql+asyncpg://user:pass@host/db``.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class SQLAlchemyPool:
    def __init__(self, dsn: str, pool_size: int = 10, max_overflow: int = 5) -> None:
        self.dsn = dsn
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.engine: Optional[AsyncEngine] = None
        self.sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None

    async def initialize(self) -> None:
        if self.engine is None:
            self.engine = create_async_engine(
                self.dsn, pool_size=self.pool_size, max_overflow=self.max_overflow, pool_pre_ping=True
            )
            self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)
            logger.info("SQLAlchemy engine initialized")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """``async with pool.session() as s:`` — the session is always closed afterwards."""
        if self.sessionmaker is None:
            await self.initialize()
        assert self.sessionmaker is not None
        async with self.sessionmaker() as session:
            yield session

    async def close(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.sessionmaker = None
            logger.info("SQLAlchemy engine closed")
