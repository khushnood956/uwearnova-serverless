"""
Role-Based Access Control (RBAC) Database Models
Follows MySQL 8.0 schema specifications in docs/backend/02-database-design.md.
"""

from typing import List, Optional
from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.base import Base, IDMixin, TimestampMixin

# Association table between roles and permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        BigInteger,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "permission_id",
        BigInteger,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)

# Association table between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "role_id",
        BigInteger,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


class Role(Base, IDMixin, TimestampMixin):
    """Role definition representing permissions granted to staff, customers, or admins."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="System role identifier (e.g. store_admin, order_manager)",
    )

    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Human-readable title for role in staff dashboards",
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Description of operational scope for this role",
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if built-in system role that cannot be deleted",
    )

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )


class Permission(Base, IDMixin):
    """Granular permission code checked by protected backend route dependencies."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique permission key (e.g. products.create, orders.read)",
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable explanation of granted capability",
    )

    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Functional domain category (e.g. catalog, orders, system)",
    )

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )
