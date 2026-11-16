"""
Audit Logging Database Model
Records sensitive administrative and operational actions for compliance and security auditing.
Follows docs/backend/02-database-design.md and docs/backend/03-dashboards-and-rbac.md.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base import Base, IDMixin


class AuditLog(Base, IDMixin):
    """Audit log entry capturing who did what, to what target, and when."""

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Actor user ID performing the action, null if unauthenticated system event",
    )

    actor_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email snapshot of actor at time of action",
    )

    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Action performed (e.g. staff.create, role.assign, customer.disable)",
    )

    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Target entity type (e.g. user, role, product, order)",
    )

    entity_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Target entity identifier",
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address initiating the action",
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Client User-Agent header",
    )

    details: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True,
        comment="JSON-formatted metadata capturing before/after or change parameters",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="UTC timestamp when action occurred",
    )
