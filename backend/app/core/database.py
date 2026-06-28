"""Async SQLAlchemy engine, session factory, and first-run schema setup.

Day 1 uses ``Base.metadata.create_all`` for speed. Alembic migrations are
introduced on Day 2 once the schema stabilises (see README roadmap).
"""

import asyncio
import ssl as ssl_lib
from collections.abc import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _prepare_url(url: str) -> tuple[str, dict]:
    """Normalise a Postgres URL for asyncpg and pull SSL out of the query string.

    Hosted Postgres (Neon/Supabase) hands out ``postgresql://...?sslmode=require``.
    asyncpg needs the ``postgresql+asyncpg://`` driver and doesn't understand the
    libpq ``sslmode``/``channel_binding`` params, so we strip them and pass an SSL
    context via connect_args instead. Local dev URLs pass through unchanged.
    """
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    connect_args: dict = {}
    if sslmode and sslmode != "disable":
        connect_args["ssl"] = ssl_lib.create_default_context()
    cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return cleaned, connect_args


_db_url, _connect_args = _prepare_url(settings.database_url)
engine = create_async_engine(
    _db_url, connect_args=_connect_args, pool_pre_ping=True, future=True
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped async session."""
    async with SessionLocal() as session:
        yield session


async def init_db(retries: int = 8, delay: float = 2.0) -> None:
    """Enable pgvector and create tables. Idempotent — safe on every boot.

    Retries the first connection: serverless Postgres (Neon free tier) suspends
    when idle and the first connection on boot can fail while the compute wakes.
    """
    # Importing the models package registers every model on Base.metadata.
    from app import models  # noqa: F401

    log = structlog.get_logger()
    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as exc:  # noqa: BLE001 — transient cold-start/DNS failures
            if attempt == retries:
                raise
            log.warning("db_connect_retry", attempt=attempt, error=str(exc)[:120])
            await asyncio.sleep(delay)
