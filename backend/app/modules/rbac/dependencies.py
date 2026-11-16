"""
Authorization Dependencies
Reusable permission and role check dependencies for protecting backend endpoints.
Ensures frontend visibility is NEVER treated as authorization.
"""

from typing import Callable, List
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import AppException
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.rbac.service import get_user_permissions


def require_permission(required_permission: str) -> Callable:
    """
    Dependency factory verifying that the authenticated user possesses the specific permission.
    Rejects unauthorized access with HTTP 403 FORBIDDEN.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_perms = await get_user_permissions(db, current_user.id)

        if required_permission not in user_perms:
            raise AppException(
                message=f"Access denied: Missing required permission '{required_permission}'.",
                code="INSUFFICIENT_PERMISSIONS",
                status_code=403,
            )
        return current_user

    return permission_checker


def require_any_permission(required_permissions: List[str]) -> Callable:
    """Dependency verifying that the user possesses at least one of the listed permissions."""
    async def any_permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_perms = await get_user_permissions(db, current_user.id)

        if not any(perm in user_perms for perm in required_permissions):
            raise AppException(
                message="Access denied: Insufficient operational permissions.",
                code="INSUFFICIENT_PERMISSIONS",
                status_code=403,
            )
        return current_user

    return any_permission_checker


def require_admin() -> Callable:
    """Dependency verifying that the user is a platform or store administrator."""
    async def admin_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.user_type == "admin":
            return current_user

        user_perms = await get_user_permissions(db, current_user.id)
        if "roles.manage" in user_perms or "settings.manage" in user_perms:
            return current_user

        raise AppException(
            message="Access denied: Administrator privileges required.",
            code="ADMIN_REQUIRED",
            status_code=403,
        )

    return admin_checker


def require_staff() -> Callable:
    """Dependency verifying that the user is an operational staff member or administrator."""
    async def staff_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.user_type in ("staff", "admin"):
            return current_user

        raise AppException(
            message="Access denied: Operational staff privileges required.",
            code="STAFF_REQUIRED",
            status_code=403,
        )

    return staff_checker
