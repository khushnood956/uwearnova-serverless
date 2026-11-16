"""
Database Connection & Session Management Module
Configures SQLAlchemy 2.x async engine, connection pool, and FastAPI session dependency.
"""

import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings
import app.core.models  # noqa: F401 - Register domain models in Base.metadata

logger = logging.getLogger("uninova.database")
settings = get_settings()


def build_async_engine(database_url: str) -> AsyncEngine:
    """Build an AsyncEngine configured with robust connection pooling."""
    connect_args = {}
    is_sqlite = database_url.startswith("sqlite")

    if not is_sqlite:
        connect_args["connect_timeout"] = 5

    engine_kwargs = {
        "echo": settings.DEBUG and settings.APP_ENV == "development",
        "future": True,
    }

    if not is_sqlite:
        engine_kwargs.update({
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": settings.DB_POOL_PRE_PING,
            "connect_args": connect_args,
        })

    return create_async_engine(database_url, **engine_kwargs)


# Primary asynchronous database engine
async_engine = build_async_engine(settings.async_database_url)

# Asynchronous session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
async_session_factory = AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an isolated transactional database session.
    Commits on successful completion, rolls back on exceptions, and ensures session closure.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health(engine: AsyncEngine = async_engine) -> bool:
    """
    Execute a lightweight ping query ('SELECT 1') to verify database connectivity.
    Returns True if healthy, False if unreachable or disconnected.
    """
    import asyncio
    try:
        async with asyncio.timeout(2.0):
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                val = result.scalar()
                return val == 1
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return False
