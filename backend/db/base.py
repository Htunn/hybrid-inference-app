"""
db/base.py — Async SQLAlchemy engine, session factory, and init_db.

DATABASE_URL must be an asyncpg connection string, e.g.:
    postgresql+asyncpg://rag:secret@postgres:5432/rag_db

init_db() is called once at FastAPI lifespan startup. It:
  1. Enables the pgvector extension (requires superuser or CREATE EXTENSION privilege).
  2. Creates all tables defined in models.py if they don't already exist.
"""

import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://rag:rag@localhost:5432/rag_db",
)

# Pool size kept small — this is a single-node app, not a multi-worker cluster.
engine = create_async_engine(
    _DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields a database session per request."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create the pgvector extension and all tables on startup."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialised (tables + pgvector extension ready)")
