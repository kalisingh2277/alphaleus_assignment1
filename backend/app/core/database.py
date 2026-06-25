"""Async SQLAlchemy engine, session factory, and first-run schema setup.

Day 1 uses ``Base.metadata.create_all`` for speed. Alembic migrations are
introduced on Day 2 once the schema stabilises (see README roadmap).
"""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped async session."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Enable pgvector and create tables. Idempotent — safe on every boot."""
    # Importing the models package registers every model on Base.metadata.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
