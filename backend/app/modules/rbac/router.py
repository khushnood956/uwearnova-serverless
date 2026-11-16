"""
RBAC Administrative API Endpoints
Provides role inspection and role assignment capabilities with audit logging.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.rbac.dependencies import require_permission
from app.modules.rbac.schemas import AssignRoleRequest, RoleResponse
from app.modules.rbac.service import assign_role_to_user, list_roles, remove_role_from_user

router = APIRouter(prefix="/admin/roles", tags=["Admin: Roles & Permissions"])


@router.get(
    "",
    response_model=List[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="List All Roles and Permissions",
)
async def get_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("roles.read")),
) -> List[RoleResponse]:
    roles = await list_roles(db)
    return [RoleResponse.model_validate(r) for r in roles]


@router.post(
    "/users/{user_id}/assign",
    status_code=status.HTTP_200_OK,
    summary="Assign Role to User",
)
async def assign_role(
    user_id: int,
    req: AssignRoleRequest,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    await assign_role_to_user(
        db,
        target_user_id=user_id,
        role_id=req.role_id,
        actor_user=current_user,
    )
    return {"message": "Role successfully assigned and audited."}


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Role Assignment from User",
)
async def remove_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    await remove_role_from_user(
        db,
        target_user_id=user_id,
        role_id=role_id,
        actor_user=current_user,
    )
    return {"message": "Role successfully revoked and audited."}
