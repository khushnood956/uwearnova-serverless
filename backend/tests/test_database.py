"""
Unit & Integration Tests for Database Foundation (Module M03)
Tests base model conventions, connection pooling, session lifecycle, and health probes.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import String, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IDMixin, TimestampMixin, NAMING_CONVENTION
from app.core.config import get_settings
from app.core.database import (
    build_async_engine,
    check_database_health,
    get_db,
)


# Concrete model for convention testing
class SampleTestModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "sample_test_models"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


def test_naming_convention_present():
    """Verify that standardized metadata naming conventions are applied."""
    assert Base.metadata.naming_convention == NAMING_CONVENTION
    assert NAMING_CONVENTION["fk"] == "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    assert NAMING_CONVENTION["uq"] == "uq_%(table_name)s_%(column_0_name)s"


def test_base_model_mixins():
    """Verify that IDMixin and TimestampMixin provide the expected columns."""
    table = SampleTestModel.__table__
    assert "id" in table.c
    assert "created_at" in table.c
    assert "updated_at" in table.c
    assert table.c.id.primary_key is True


def test_engine_pool_configuration():
    """Verify that connection pool configuration properties are honored."""
    settings = get_settings()
    assert settings.DB_POOL_SIZE == 10
    assert settings.DB_MAX_OVERFLOW == 20
    assert settings.DB_POOL_RECYCLE == 1800
    assert settings.DB_POOL_PRE_PING is True


@pytest.mark.asyncio
async def test_database_health_check_with_active_engine():
    """Verify check_database_health against a working test engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    is_healthy = await check_database_health(engine)
    assert is_healthy is True
    await engine.dispose()


@pytest.mark.asyncio
async def test_database_health_check_with_failing_engine():
    """Verify check_database_health gracefully returns False when unreachable."""
    # Use invalid host to trigger immediate connection failure
    unreachable_engine = create_async_engine(
        "mysql+aiomysql://invalid_user:invalid_pass@127.0.0.1:59999/invalid_db",
        connect_args={"connect_timeout": 1},
    )
    is_healthy = await check_database_health(unreachable_engine)
    assert is_healthy is False
    await unreachable_engine.dispose()


@pytest.mark.asyncio
async def test_session_lifecycle_and_transaction():
    """Verify session commit/rollback and query execution."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import async_sessionmaker
    test_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with test_session_maker() as session:
        item = SampleTestModel(name="Test Item")
        session.add(item)
        await session.commit()
        assert item.id is not None

        result = await session.execute(select(SampleTestModel).where(SampleTestModel.id == item.id))
        queried = result.scalar_one_or_none()
        assert queried is not None
        assert queried.name == "Test Item"

    await engine.dispose()
