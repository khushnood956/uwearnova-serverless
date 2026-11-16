"""
Audit Service Module
Records and retrieves immutable audit trail records for compliance and operational transparency.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.models import AuditLog


async def log_audit_event(
    db: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    user_id: Optional[int] = None,
    actor_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Persist an audit log record for a sensitive operational action."""
    details_str = json.dumps(details, default=str) if details else None

    log_entry = AuditLog(
        user_id=user_id,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details_str,
    )
    db.add(log_entry)
    await db.flush()
    return log_entry


async def get_audit_logs(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
) -> Tuple[List[AuditLog], int]:
    """Retrieve paginated audit logs with optional filtering."""
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)

    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
        count_query = count_query.where(AuditLog.entity_type == entity_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total
