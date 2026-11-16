"""
Audit Log Inspection API Endpoints
Provides administrative visibility into sensitive operational actions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.audit.schemas import AuditLogListResponse, AuditLogResponse
from app.modules.audit.service import get_audit_logs
from app.modules.auth.models import User
from app.modules.rbac.dependencies import require_permission

router = APIRouter(prefix="/admin/audit-logs", tags=["Admin: Audit Trail"])


@router.get(
    "",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Audit Log Records",
)
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None, description="Filter by action code"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("audit.read")),
) -> AuditLogListResponse:
    items, total = await get_audit_logs(
        db,
        limit=limit,
        offset=offset,
        action=action,
        entity_type=entity_type,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
    )
