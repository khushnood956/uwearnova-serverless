"""
Database Model Base & Convention Module
Defines DeclarativeBase, naming conventions, and common mixins.
Follows MySQL 8.0 schema specifications in docs/backend/02-database-design.md.
"""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import BigInteger, DateTime, Integer, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit naming convention for database constraints to ensure repeatable Alembic migrations
# and prevent anonymous foreign key or unique constraint errors in MySQL
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy domain models with standardized metadata."""

    metadata = metadata

    def __repr__(self) -> str:
        """Informative string representation for debugging and logs."""
        attrs = []
        for key in self.__mapper__.column_attrs.keys():
            attrs.append(f"{key}={getattr(self, key)!r}")
        return f"<{self.__class__.__name__}({', '.join(attrs)})>"


class IDMixin:
    """Standardized 64-bit integer primary key (BIGINT in MySQL, Integer in SQLite test dialect)."""

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
        comment="Primary unique identifier",
    )


class TimestampMixin:
    """Standardized UTC timestamp mixin for creation and modification tracking."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        comment="UTC timestamp when record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="UTC timestamp when record was last updated",
    )
