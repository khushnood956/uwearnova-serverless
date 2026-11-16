"""
RBAC & Audit Logging Tests
Verifies roles, permissions, privilege escalation prevention, and audit recording.
"""

import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.core.security import create_access_token
from app.modules.rbac.models import Permission, Role, user_roles
from app.modules.rbac.permissions import ALL_PERMISSIONS, SYSTEM_ROLES
from app.modules.rbac.service import (
    assign_role_to_user,
    get_user_permissions,
    seed_system_roles_and_permissions,
)


@pytest.fixture
async def seeded_rbac() -> None:
    """Fixture that seeds roles and permissions."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await session.commit()


async def create_user_helper(
    session: AsyncSession,
    email: str,
    user_type: str = "customer",
) -> User:
    """Helper to create and commit a user in the test database."""
    user = User(
        email=email,
        password_hash=hash_password("SecurePassword123!"),
        status="active",
        user_type=user_type,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def auth_header_for_user(user: User) -> dict:
    """Helper to generate Authorization header for a user."""
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_seed_roles_and_permissions_idempotent():
    """Verify seeding creates all permissions and roles, and running twice does not duplicate."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)
        await session.commit()

        # Count permissions and roles
        perms = (await session.execute(select(Permission))).scalars().all()
        roles = (await session.execute(select(Role))).scalars().all()

        assert len(perms) == len(ALL_PERMISSIONS)
        assert len(roles) == len(SYSTEM_ROLES)

        # Run again to ensure idempotency
        await seed_system_roles_and_permissions(session)
        await session.commit()

        perms_second = (await session.execute(select(Permission))).scalars().all()
        roles_second = (await session.execute(select(Role))).scalars().all()

        assert len(perms_second) == len(ALL_PERMISSIONS)
        assert len(roles_second) == len(SYSTEM_ROLES)


@pytest.mark.asyncio
async def test_get_user_permissions_admin_and_staff(seeded_rbac):
    """Admin has all permissions; staff user receives only assigned role permissions."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_helper(session, "admin@uwearnova.com", user_type="admin")
        customer = await create_user_helper(session, "cust@uwearnova.com", user_type="customer")
        staff = await create_user_helper(session, "orderstaff@uwearnova.com", user_type="staff")

        # Admin gets all
        admin_perms = await get_user_permissions(session, admin.id)
        assert len(admin_perms) == len(ALL_PERMISSIONS)
        assert "roles.manage" in admin_perms
        assert "orders.read" in admin_perms

        # Customer has none by default
        cust_perms = await get_user_permissions(session, customer.id)
        assert len(cust_perms) == 0

        # Assign order_manager role to staff
        order_mgr_role = (await session.execute(select(Role).where(Role.name == "order_manager"))).scalar_one()
        await assign_role_to_user(session, staff.id, order_mgr_role.id, actor_user=admin)
        await session.commit()

        staff_perms = await get_user_permissions(session, staff.id)
        assert "orders.read" in staff_perms
        assert "orders.update" in staff_perms
        assert "roles.manage" not in staff_perms
        assert "inventory.adjust" not in staff_perms


@pytest.mark.asyncio
async def test_roles_endpoint_authorization(async_client: AsyncClient, seeded_rbac):
    """GET /api/v1/admin/roles requires authentication and roles.read permission."""
    from tests.conftest import TestingSessionLocal

    # 1. Unauthenticated -> 401
    resp = await async_client.get("/api/v1/admin/roles")
    assert resp.status_code == 401

    async with TestingSessionLocal() as session:
        customer = await create_user_helper(session, "regular@uwearnova.com", user_type="customer")
        admin = await create_user_helper(session, "superadmin@uwearnova.com", user_type="admin")

    # 2. Customer -> 403 Insufficient permissions
    cust_headers = auth_header_for_user(customer)
    resp = await async_client.get("/api/v1/admin/roles", headers=cust_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # 3. Admin -> 200 OK
    admin_headers = auth_header_for_user(admin)
    resp = await async_client.get("/api/v1/admin/roles", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= len(SYSTEM_ROLES)
    role_names = [r["name"] for r in data]
    assert "store_admin" in role_names
    assert "order_manager" in role_names


@pytest.mark.asyncio
async def test_role_assignment_and_audit_log(async_client: AsyncClient, seeded_rbac):
    """Assigning and removing roles updates user status and records immutable audit logs."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_helper(session, "auditor_admin@uwearnova.com", user_type="admin")
        target_user = await create_user_helper(session, "promoted@uwearnova.com", user_type="customer")
        role_res = await session.execute(select(Role).where(Role.name == "fulfillment_staff"))
        fulfillment_role = role_res.scalar_one()

    admin_headers = auth_header_for_user(admin)

    # 1. Assign role via API
    assign_resp = await async_client.post(
        f"/api/v1/admin/roles/users/{target_user.id}/assign",
        json={"role_id": fulfillment_role.id},
        headers=admin_headers,
    )
    assert assign_resp.status_code == 200

    # Verify user_type was updated to 'staff'
    async with TestingSessionLocal() as session:
        refreshed_user = (await session.execute(select(User).where(User.id == target_user.id))).scalar_one()
        assert refreshed_user.user_type == "staff"

        # Verify audit log was recorded
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "role.assigned",
                AuditLog.entity_id == str(target_user.id),
            )
        )
        log_entry = audit_res.scalar_one()
        assert log_entry.user_id == admin.id
        assert log_entry.actor_email == admin.email
        assert json.loads(log_entry.details)["assigned_role_name"] == "fulfillment_staff"

    # 2. Remove role via API
    remove_resp = await async_client.delete(
        f"/api/v1/admin/roles/users/{target_user.id}/roles/{fulfillment_role.id}",
        headers=admin_headers,
    )
    assert remove_resp.status_code == 200

    # Verify audit log for removal
    async with TestingSessionLocal() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "role.removed",
                AuditLog.entity_id == str(target_user.id),
            )
        )
        removal_entry = audit_res.scalar_one()
        assert removal_entry.user_id == admin.id
        assert json.loads(removal_entry.details)["removed_role_name"] == "fulfillment_staff"


@pytest.mark.asyncio
async def test_privilege_escalation_prevention(async_client: AsyncClient, seeded_rbac):
    """
    Staff user cannot assign a role containing permissions they do not possess,
    even if they somehow have roles.manage permission.
    """
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_helper(session, "boss@uwearnova.com", user_type="admin")
        limited_staff = await create_user_helper(session, "subadmin@uwearnova.com", user_type="staff")
        target_user = await create_user_helper(session, "target@uwearnova.com", user_type="customer")

        # Create a custom limited role with 'roles.manage' and 'orders.read'
        limited_role = Role(name="limited_lead", display_name="Limited Lead", description="Test", is_system=False, permissions=[])
        roles_manage_perm = (await session.execute(select(Permission).where(Permission.code == "roles.manage"))).scalar_one()
        orders_read_perm = (await session.execute(select(Permission).where(Permission.code == "orders.read"))).scalar_one()
        limited_role.permissions.extend([roles_manage_perm, orders_read_perm])
        session.add(limited_role)
        await session.flush()

        # Assign limited_role to limited_staff
        await session.execute(user_roles.insert().values(user_id=limited_staff.id, role_id=limited_role.id))

        # Retrieve store_admin role (which has all permissions)
        store_admin_role = (await session.execute(select(Role).where(Role.name == "store_admin"))).scalar_one()
        await session.commit()

    limited_headers = auth_header_for_user(limited_staff)

    # Attempt to assign store_admin (escalation!)
    resp = await async_client.post(
        f"/api/v1/admin/roles/users/{target_user.id}/assign",
        json={"role_id": store_admin_role.id},
        headers=limited_headers,
    )
    assert resp.status_code == 403
    error_data = resp.json()["error"]
    assert error_data["code"] == "PRIVILEGE_ESCALATION_PREVENTED"


@pytest.mark.asyncio
async def test_audit_logs_inspection_endpoint(async_client: AsyncClient, seeded_rbac):
    """GET /api/v1/admin/audit-logs requires audit.read and returns structured trail."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_helper(session, "auditor@uwearnova.com", user_type="admin")
        customer = await create_user_helper(session, "curious_customer@uwearnova.com", user_type="customer")

        # Insert some sample audit logs via log_audit_event
        await log_audit_event(
            session,
            action="order.status_update",
            entity_type="order",
            entity_id="101",
            user_id=admin.id,
            actor_email=admin.email,
            details={"old_status": "pending", "new_status": "processing"},
        )
        await log_audit_event(
            session,
            action="inventory.adjustment",
            entity_type="inventory",
            entity_id="prod_variant_5",
            user_id=admin.id,
            actor_email=admin.email,
            details={"delta": -2, "reason": "damaged_garment"},
        )
        await session.commit()

    # 1. Denied for customer
    cust_headers = auth_header_for_user(customer)
    resp = await async_client.get("/api/v1/admin/audit-logs", headers=cust_headers)
    assert resp.status_code == 403

    # 2. Allowed for admin
    admin_headers = auth_header_for_user(admin)
    resp = await async_client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    actions = [item["action"] for item in data["items"]]
    assert "order.status_update" in actions
    assert "inventory.adjustment" in actions

    # 3. Filter by action
    filter_resp = await async_client.get("/api/v1/admin/audit-logs?action=inventory.adjustment", headers=admin_headers)
    assert filter_resp.status_code == 200
    filter_data = filter_resp.json()
    assert filter_data["total"] == 1
    assert filter_data["items"][0]["action"] == "inventory.adjustment"
    parsed_details = json.loads(filter_data["items"][0]["details"])
    assert parsed_details["reason"] == "damaged_garment"


@pytest.mark.asyncio
async def test_authorization_dependency_callables(seeded_rbac):
    """Directly test authorization dependency callables (require_permission, require_staff, require_admin)."""
    from tests.conftest import TestingSessionLocal
    from app.common.errors import AppException
    from app.modules.rbac.dependencies import (
        require_admin,
        require_any_permission,
        require_permission,
        require_staff,
    )

    async with TestingSessionLocal() as session:
        admin = await create_user_helper(session, "dep_admin@uwearnova.com", user_type="admin")
        staff = await create_user_helper(session, "dep_staff@uwearnova.com", user_type="staff")
        customer = await create_user_helper(session, "dep_cust@uwearnova.com", user_type="customer")

        # 1. require_staff
        staff_checker = require_staff()
        assert (await staff_checker(staff)) == staff
        assert (await staff_checker(admin)) == admin
        with pytest.raises(AppException) as exc:
            await staff_checker(customer)
        assert exc.value.status_code == 403
        assert exc.value.code == "STAFF_REQUIRED"

        # 2. require_admin
        admin_checker = require_admin()
        assert (await admin_checker(admin, session)) == admin
        with pytest.raises(AppException) as exc:
            await admin_checker(staff, session)
        assert exc.value.status_code == 403
        assert exc.value.code == "ADMIN_REQUIRED"

        # 3. require_any_permission
        any_perm_checker = require_any_permission(["orders.read", "products.read"])
        # Admin has all permissions, passes
        assert (await any_perm_checker(admin, session)) == admin
        # Customer has none, raises
        with pytest.raises(AppException) as exc:
            await any_perm_checker(customer, session)
        assert exc.value.status_code == 403
        assert exc.value.code == "INSUFFICIENT_PERMISSIONS"

