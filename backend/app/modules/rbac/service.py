"""
RBAC Service Layer
Manages roles, permissions, user role assignments, privilege escalation prevention, and seeding.
"""

from typing import List, Optional, Set
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import AppException
from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.rbac.models import Permission, Role, role_permissions, user_roles
from app.modules.rbac.permissions import ALL_PERMISSIONS, SYSTEM_ROLES


async def seed_system_roles_and_permissions(db: AsyncSession) -> None:
    """Ensure all standard system permissions and roles exist in the database."""
    # 1. Seed permissions
    existing_perms_res = await db.execute(select(Permission))
    existing_perms = {p.code: p for p in existing_perms_res.scalars().all()}

    for perm_def in ALL_PERMISSIONS:
        if perm_def.code not in existing_perms:
            perm = Permission(
                code=perm_def.code,
                description=perm_def.description,
                category=perm_def.category,
            )
            db.add(perm)
            existing_perms[perm_def.code] = perm

    await db.flush()

    # 2. Seed roles and associations
    existing_roles_res = await db.execute(select(Role).options(selectinload(Role.permissions)))
    existing_roles = {r.name: r for r in existing_roles_res.scalars().all()}

    for role_name, role_meta in SYSTEM_ROLES.items():
        if role_name not in existing_roles:
            role = Role(
                name=role_name,
                display_name=role_meta["display_name"],
                description=role_meta["description"],
                is_system=True,
                permissions=[],
            )
            db.add(role)
            existing_roles[role_name] = role

        role = existing_roles[role_name]
        desired_perm_codes = set(role_meta["permissions"])
        current_perm_codes = {p.code for p in role.permissions}

        missing_codes = desired_perm_codes - current_perm_codes
        for code in missing_codes:
            if code in existing_perms:
                role.permissions.append(existing_perms[code])

    await db.flush()


async def get_user_permissions(db: AsyncSession, user_id: int) -> Set[str]:
    """Retrieve the set of all active permission codes granted to the user."""
    # 1. Check if user is platform admin
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        return set()

    if user.user_type == "admin":
        return {p.code for p in ALL_PERMISSIONS}

    # 2. Query permissions through assigned roles
    query = (
        select(Permission.code)
        .join(role_permissions, Permission.id == role_permissions.c.permission_id)
        .join(user_roles, role_permissions.c.role_id == user_roles.c.role_id)
        .where(user_roles.c.user_id == user_id)
    )
    result = await db.execute(query)
    perms = set(result.scalars().all())

    return perms


async def list_roles(db: AsyncSession) -> List[Role]:
    """Return all roles with preloaded permissions."""
    query = select(Role).options(selectinload(Role.permissions)).order_by(Role.id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def assign_role_to_user(
    db: AsyncSession,
    target_user_id: int,
    role_id: int,
    actor_user: User,
) -> None:
    """
    Assign a role to a user with strict privilege escalation prevention and audit recording.
    """
    # 1. Target user verification
    target_res = await db.execute(select(User).where(User.id == target_user_id))
    target_user = target_res.scalar_one_or_none()
    if not target_user:
        raise AppException(message="Target user not found.", code="USER_NOT_FOUND", status_code=404)

    # 2. Role verification
    role_res = await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id))
    role = role_res.scalar_one_or_none()
    if not role:
        raise AppException(message="Role not found.", code="ROLE_NOT_FOUND", status_code=404)

    # 3. Privilege Escalation Prevention
    # A non-admin user cannot assign roles unless they possess the 'roles.manage' permission
    # AND the role being assigned cannot contain permissions the actor does not possess!
    actor_perms = await get_user_permissions(db, actor_user.id)
    if "roles.manage" not in actor_perms and actor_user.user_type != "admin":
        raise AppException(
            message="Unauthorized to manage user roles.",
            code="FORBIDDEN",
            status_code=403,
        )

    # Prevent non-admin from escalating privileges by granting a role with higher permissions
    if actor_user.user_type != "admin":
        role_perm_codes = {p.code for p in role.permissions}
        escalated_perms = role_perm_codes - actor_perms
        if escalated_perms:
            raise AppException(
                message="Privilege escalation prevented: You cannot assign roles with permissions you do not possess.",
                code="PRIVILEGE_ESCALATION_PREVENTED",
                status_code=403,
            )

    # 4. Check if already assigned
    existing_res = await db.execute(
        select(user_roles).where(
            user_roles.c.user_id == target_user_id,
            user_roles.c.role_id == role_id,
        )
    )
    if existing_res.first():
        return  # Already assigned

    # 5. Insert association
    await db.execute(insert(user_roles).values(user_id=target_user_id, role_id=role_id))

    # Update user_type to 'staff' if target is assigned a staff role
    if role.name != "customer" and target_user.user_type == "customer":
        target_user.user_type = "staff"

    # 6. Record audit log
    await log_audit_event(
        db,
        action="role.assigned",
        entity_type="user",
        entity_id=str(target_user_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "assigned_role_id": role_id,
            "assigned_role_name": role.name,
            "target_user_email": target_user.email,
        },
    )
    await db.flush()


async def remove_role_from_user(
    db: AsyncSession,
    target_user_id: int,
    role_id: int,
    actor_user: User,
) -> None:
    """Remove a role assignment from a user with audit recording."""
    actor_perms = await get_user_permissions(db, actor_user.id)
    if "roles.manage" not in actor_perms and actor_user.user_type != "admin":
        raise AppException(message="Unauthorized to manage user roles.", code="FORBIDDEN", status_code=403)

    target_res = await db.execute(select(User).where(User.id == target_user_id))
    target_user = target_res.scalar_one_or_none()
    if not target_user:
        raise AppException(message="Target user not found.", code="USER_NOT_FOUND", status_code=404)

    role_res = await db.execute(select(Role).where(Role.id == role_id))
    role = role_res.scalar_one_or_none()
    if not role:
        raise AppException(message="Role not found.", code="ROLE_NOT_FOUND", status_code=404)

    # Execute removal
    stmt = delete(user_roles).where(
        user_roles.c.user_id == target_user_id,
        user_roles.c.role_id == role_id,
    )
    await db.execute(stmt)

    # Record audit log
    await log_audit_event(
        db,
        action="role.removed",
        entity_type="user",
        entity_id=str(target_user_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "removed_role_id": role_id,
            "removed_role_name": role.name,
            "target_user_email": target_user.email,
        },
    )
    await db.flush()
