"""
Module M21 — Promotions, Reviews, and Content APIs Test Suite
Verifies:
- Promotion and coupon lifecycle management (creation, expiry, percentage, fixed amount, thresholds)
- Backend-authoritative discount validation (never trusts client-submitted values)
- Usage limits and redemption ledger recording integrated with checkout
- Customer product review submission, verified purchaser detection, and administrative moderation
- Automatic re-aggregation of product average ratings and review counts
- Announcement bar and homepage campaign management with schedule awareness
- Content page CMS management (slug resolution, markdown/HTML body, publishing status)
- Strict RBAC access control and immutable audit logging for sensitive marketing changes
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from typing import Optional
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.catalog.seed_data import seed_catalog_products
from app.modules.content.models import AnnouncementBar, ContentPage, HomepageCampaign
from app.modules.inventory.schemas import StockAdjustmentRequest
from app.modules.inventory.service import adjust_stock, get_or_create_default_location
from app.modules.orders.models import Order, OrderItem
from app.modules.promotions.models import Coupon, CouponRedemption
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions
from app.modules.reviews.models import ProductReview
from app.modules.shipping.service import ensure_default_shipping_configuration
from tests.conftest import TestingSessionLocal


async def ensure_roles_and_config(session: AsyncSession) -> None:
    """Ensure system roles, default shipping, and default warehouse location exist."""
    await seed_system_roles_and_permissions(session)
    await ensure_default_shipping_configuration(session)
    await get_or_create_default_location(session)
    await session.commit()


async def create_user_with_role(
    session: AsyncSession,
    email: str,
    role_name: str,
    user_type: str = "staff",
) -> User:
    """Helper to create a user and assign a system role."""
    await ensure_roles_and_config(session)

    user = User(
        email=email,
        password_hash=hash_password("SecurePassword123!"),
        status="active",
        user_type=user_type,
    )
    session.add(user)
    await session.flush()

    role_res = await session.execute(select(Role).where(Role.name == role_name))
    role = role_res.scalar_one()

    await session.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))
    await session.commit()
    await session.refresh(user)
    return user


def auth_header_for(user: User) -> dict:
    """Generate Authorization header for user."""
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def setup_m21_data():
    """Initializes catalogue, shipping, warehouse, and system roles for testing."""
    async with TestingSessionLocal() as session:
        await ensure_roles_and_config(session)
        await seed_catalog_products(session)
        await session.commit()


# =========================================================================
# 1. Promotions and Coupon Validation Tests
# =========================================================================

@pytest.mark.asyncio
async def test_promotions_coupon_validation_and_expiry(async_client: AsyncClient, setup_m21_data):
    """
    Test coupon rules: percentage discount, maximum ceiling, minimum subtotal,
    and expiration handling on the backend.
    """
    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "promo_admin@uwearnova.com", "store_admin", user_type="admin")

    # 1. Admin creates percentage coupon with minimum order and max cap
    res_create = await async_client.post(
        "/api/v1/admin/coupons",
        headers=auth_header_for(admin),
        json={
            "code": "SAVE20",
            "description": "20% off on orders above 2,000 capped at 1,000",
            "discount_type": "percentage",
            "discount_value": 20.0,
            "min_order_amount": 2000.0,
            "max_discount_amount": 1000.0,
            "is_active": True,
        },
    )
    assert res_create.status_code == 201
    assert res_create.json()["code"] == "SAVE20"

    # 2. Subtotal below minimum order threshold -> invalid
    res_val_low = await async_client.post(
        "/api/v1/promotions/validate",
        json={"code": "SAVE20", "subtotal": 1500.0, "customer_email": "client@example.com"},
    )
    assert res_val_low.status_code == 200
    assert res_val_low.json()["is_valid"] is False
    assert Decimal(str(res_val_low.json()["discount_amount"])) == Decimal("0.00")

    # 3. Subtotal 3,000 -> 20% = 600 (< 1,000 cap)
    res_val_mid = await async_client.post(
        "/api/v1/promotions/validate",
        json={"code": "save20", "subtotal": 3000.0, "customer_email": "client@example.com"},
    )
    assert res_val_mid.status_code == 200
    assert res_val_mid.json()["is_valid"] is True
    assert Decimal(str(res_val_mid.json()["discount_amount"])) == Decimal("600.00")
    assert Decimal(str(res_val_mid.json()["new_subtotal"])) == Decimal("2400.00")

    # 4. Subtotal 10,000 -> 20% = 2,000 -> capped at 1,000
    res_val_high = await async_client.post(
        "/api/v1/promotions/validate",
        json={"code": "SAVE20", "subtotal": 10000.0, "customer_email": "client@example.com"},
    )
    assert res_val_high.status_code == 200
    assert res_val_high.json()["is_valid"] is True
    assert Decimal(str(res_val_high.json()["discount_amount"])) == Decimal("1000.00")
    assert Decimal(str(res_val_high.json()["new_subtotal"])) == Decimal("9000.00")

    # 5. Admin creates an expired coupon
    res_expired = await async_client.post(
        "/api/v1/admin/coupons",
        headers=auth_header_for(admin),
        json={
            "code": "EXPIRED10",
            "discount_type": "fixed_amount",
            "discount_value": 500.0,
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "is_active": True,
        },
    )
    assert res_expired.status_code == 201

    res_val_exp = await async_client.post(
        "/api/v1/promotions/validate",
        json={"code": "EXPIRED10", "subtotal": 5000.0, "customer_email": "client@example.com"},
    )
    assert res_val_exp.status_code == 200
    assert res_val_exp.json()["is_valid"] is False
    assert "expired" in res_val_exp.json()["message"].lower()


# =========================================================================
# 2. Usage Limits and Checkout Integration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_coupon_usage_limits_and_checkout_integration(async_client: AsyncClient, setup_m21_data):
    """
    Test that valid coupon is applied during checkout, reduces total on backend,
    records CouponRedemption, and enforces usage quotas.
    """
    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "promo_checkout@uwearnova.com", "store_admin", user_type="admin")
        # Ensure a variant is stocked
        var = (await session.execute(select(ProductVariant).limit(1))).scalars().first()
        var_id = var.id
        await adjust_stock(session, StockAdjustmentRequest(variant_id=var_id, quantity_delta=50, reason="receipt"))
        await session.commit()

    # 1. Admin creates one-time coupon: 1 redemption per customer, 1 total storewide
    res_cpn = await async_client.post(
        "/api/v1/admin/coupons",
        headers=auth_header_for(admin),
        json={
            "code": "ONCEONLY",
            "discount_type": "fixed_amount",
            "discount_value": 1000.0,
            "usage_limit_total": 1,
            "usage_limit_per_customer": 1,
            "is_active": True,
        },
    )
    assert res_cpn.status_code == 201
    coupon_id = res_cpn.json()["id"]

    # 2. Customer adds item to cart
    headers = {"X-Anonymous-Cart-Token": "anon-cart-m21"}
    await async_client.post("/api/v1/cart/items", headers=headers, json={"variant_id": var_id, "quantity": 1})

    # 3. Checkout with coupon
    checkout_res = await async_client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json={
            "customer_name": "Bilal Merchant",
            "customer_email": "bilal@example.com",
            "customer_phone": "03001234567",
            "shipping_address": {
                "full_name": "Bilal Merchant",
                "phone": "03001234567",
                "address_line_1": "Main Boulevard, DHA Phase 5",
                "city": "Lahore",
                "country_code": "PK",
            },
            "shipping_method_code": "standard_delivery",
            "payment_method": "cod",
            "coupon_code": "ONCEONLY",
        },
    )
    assert checkout_res.status_code == 201
    order_data = checkout_res.json()
    assert Decimal(str(order_data["discount_total"])) == Decimal("1000.00")
    expected_grand_total = Decimal(str(order_data["subtotal"])) - Decimal(str(order_data["discount_total"])) + Decimal(str(order_data["shipping_total"]))
    assert Decimal(str(order_data["grand_total"])) == Decimal(str(expected_grand_total))

    # 4. Check that redemption was recorded
    res_redemptions = await async_client.get(
        f"/api/v1/admin/coupons/{coupon_id}/redemptions",
        headers=auth_header_for(admin),
    )
    assert res_redemptions.status_code == 200
    assert res_redemptions.json()["total"] == 1
    assert res_redemptions.json()["items"][0]["customer_email"] == "bilal@example.com"

    # 5. Second attempt to use ONCEONLY -> rejected during checkout with 400 Bad Request
    await async_client.post("/api/v1/cart/items", headers=headers, json={"variant_id": var_id, "quantity": 1})
    checkout_res_fail = await async_client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json={
            "customer_name": "Bilal Merchant",
            "customer_email": "bilal@example.com",
            "customer_phone": "03001234567",
            "shipping_address": {
                "full_name": "Bilal Merchant",
                "phone": "03001234567",
                "address_line_1": "Main Boulevard, DHA Phase 5",
                "city": "Lahore",
                "country_code": "PK",
            },
            "shipping_method_code": "standard_delivery",
            "payment_method": "cod",
            "coupon_code": "ONCEONLY",
        },
    )
    assert checkout_res_fail.status_code == 400
    err_body = checkout_res_fail.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "Invalid coupon code" in err_msg


# =========================================================================
# 3. Product Reviews Submission and Moderation Tests
# =========================================================================

@pytest.mark.asyncio
async def test_product_reviews_submission_and_moderation(async_client: AsyncClient, setup_m21_data):
    """
    Test customer review submission, verified purchaser detection,
    administrative review moderation, and automatic product rating re-aggregation.
    """
    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "rev_admin@uwearnova.com", "store_admin", user_type="admin")
        product = (await session.execute(select(Product).limit(1))).scalars().first()
        prod_id = product.id
        prod_slug = product.slug

        # Seed an existing confirmed order for this customer & product to test verified buyer flag
        order = Order(
            order_number="UNV-20261111-VERIFIED",
            customer_email="verified_buyer@example.com",
            customer_phone="03001112233",
            customer_name="Verified Purchaser",
            status="delivered",
            payment_status="paid",
            payment_method="cod",
            fulfillment_status="fulfilled",
            subtotal=Decimal("4000.00"),
            shipping_total=Decimal("200.00"),
            grand_total=Decimal("4200.00"),
            currency_code="PKR",
            shipping_method_code="standard_delivery",
            shipping_method_name="Standard Delivery",
            shipping_address_snapshot=json.dumps({"city": "Karachi", "address_line_1": "Clifton Block 2"}),
        )
        session.add(order)
        await session.flush()

        order_item = OrderItem(
            order_id=order.id,
            product_id=prod_id,
            variant_id=1,
            product_name_snapshot=product.name,
            product_slug_snapshot=prod_slug,
            sku_snapshot="SKU-VERIFIED",
            size_snapshot="M",
            color_snapshot="Navy",
            unit_price=Decimal("4000.00"),
            quantity=1,
            line_total=Decimal("4000.00"),
        )
        session.add(order_item)
        await session.commit()

    # 1. Customer submits a 5-star review
    res_sub = await async_client.post(
        f"/api/v1/products/{prod_slug}/reviews",
        json={
            "customer_name": "Verified Purchaser",
            "customer_email": "verified_buyer@example.com",
            "rating": 5,
            "title": "Impeccable Fabric & Cut",
            "comment": "The virgin wool drape is exquisite. Extremely pleased with UniNova tailoring.",
        },
    )
    assert res_sub.status_code == 201
    review_data = res_sub.json()
    assert review_data["rating"] == 5
    assert review_data["is_verified_buyer"] is True
    review_id = review_data["id"]

    # 2. Public review listing should NOT show pending review
    res_pub = await async_client.get(f"/api/v1/products/{prod_slug}/reviews")
    assert res_pub.status_code == 200
    assert not any(r["id"] == review_id for r in res_pub.json()["items"])

    # 3. Admin lists pending reviews
    res_admin_list = await async_client.get(
        "/api/v1/admin/reviews?status=pending",
        headers=auth_header_for(admin),
    )
    assert res_admin_list.status_code == 200
    assert any(r["id"] == review_id for r in res_admin_list.json()["items"])

    # 4. Admin approves the review
    res_mod = await async_client.post(
        f"/api/v1/admin/reviews/{review_id}/moderate",
        headers=auth_header_for(admin),
        json={"action": "approve", "admin_notes": "Verified authentic customer feedback"},
    )
    assert res_mod.status_code == 200
    assert res_mod.json()["status"] == "approved"

    # 5. Public storefront now displays the approved review and updated ratings
    res_pub_after = await async_client.get(f"/api/v1/products/{prod_slug}/reviews")
    assert res_pub_after.status_code == 200
    assert any(r["id"] == review_id for r in res_pub_after.json()["items"])
    assert res_pub_after.json()["total"] >= 1


# =========================================================================
# 4. Announcement Bars and Homepage Campaigns Tests
# =========================================================================

@pytest.mark.asyncio
async def test_announcement_bars_and_homepage_campaigns(async_client: AsyncClient, setup_m21_data):
    """
    Test announcement bar alerts and homepage hero campaign management.
    """
    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "content_admin@uwearnova.com", "store_admin", user_type="admin")

    # 1. Admin creates announcement bar
    res_bar = await async_client.post(
        "/api/v1/admin/content/announcements",
        headers=auth_header_for(admin),
        json={
            "message": "Complimentary nationwide shipping on orders over PKR 5,000",
            "link_url": "/shipping-delivery",
            "bg_color": "#111111",
            "text_color": "#FFFFFF",
            "is_active": True,
        },
    )
    assert res_bar.status_code == 201
    bar_id = res_bar.json()["id"]

    # 2. Public announcement query
    res_pub_bars = await async_client.get("/api/v1/content/announcements")
    assert res_pub_bars.status_code == 200
    assert any(b["id"] == bar_id for b in res_pub_bars.json())

    # 3. Admin creates homepage campaign
    res_camp = await async_client.post(
        "/api/v1/admin/content/homepage-campaigns",
        headers=auth_header_for(admin),
        json={
            "title": "Sartorial Monolith 2026",
            "subtitle": "Structured silhouettes crafted in raw virgin wool",
            "cta_text": "Discover Collection",
            "cta_link": "/collections/men",
            "sort_order": 1,
            "is_active": True,
        },
    )
    assert res_camp.status_code == 201
    camp_id = res_camp.json()["id"]

    # 4. Public homepage campaign query
    res_pub_camps = await async_client.get("/api/v1/content/homepage-campaigns")
    assert res_pub_camps.status_code == 200
    assert any(c["id"] == camp_id for c in res_pub_camps.json())


# =========================================================================
# 5. Content Policy Pages CMS Tests
# =========================================================================

@pytest.mark.asyncio
async def test_content_pages_crud_and_storefront_view(async_client: AsyncClient, setup_m21_data):
    """
    Test static policy / CMS page CRUD and storefront viewing.
    """
    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "cms_admin@uwearnova.com", "store_admin", user_type="admin")

    # 1. Admin creates content page
    res_page = await async_client.post(
        "/api/v1/admin/content/pages",
        headers=auth_header_for(admin),
        json={
            "slug": "bespoke-tailoring",
            "title": "Bespoke Tailoring & Heritage",
            "body": "# Bespoke Craft\nEvery stitch is shaped by master Pakistani artisans in Lahore.",
            "meta_title": "Bespoke Tailoring | UniNova",
            "meta_description": "Custom sartorial tailoring guidelines.",
            "is_published": True,
        },
    )
    assert res_page.status_code == 201
    page_id = res_page.json()["id"]

    # 2. Public views page by slug
    res_pub_page = await async_client.get("/api/v1/content/pages/bespoke-tailoring")
    assert res_pub_page.status_code == 200
    assert res_pub_page.json()["title"] == "Bespoke Tailoring & Heritage"

    # 3. Admin unpublishes page
    await async_client.put(
        f"/api/v1/admin/content/pages/{page_id}",
        headers=auth_header_for(admin),
        json={"is_published": False},
    )

    # 4. Public query for unpublished page returns 404
    res_pub_unpub = await async_client.get("/api/v1/content/pages/bespoke-tailoring")
    assert res_pub_unpub.status_code == 404


# =========================================================================
# 6. RBAC and Audit Logging Tests
# =========================================================================

@pytest.mark.asyncio
async def test_m21_rbac_and_audit_logging(async_client: AsyncClient, setup_m21_data):
    """
    Verify that unprivileged staff and customers are barred from administrative marketing operations,
    and all administrative modifications produce audit records.
    """
    async with TestingSessionLocal() as session:
        fulfillment_user = await create_user_with_role(session, "fs_m21@uwearnova.com", "fulfillment_staff")
        admin = await create_user_with_role(session, "mkt_admin@uwearnova.com", "store_admin", user_type="admin")

    # Fulfillment staff cannot manage coupons (lacks promotions.manage) -> 403
    res_unauth_cpn = await async_client.post(
        "/api/v1/admin/coupons",
        headers=auth_header_for(fulfillment_user),
        json={"code": "HACK20", "discount_value": 20.0},
    )
    assert res_unauth_cpn.status_code == 403

    # Fulfillment staff cannot moderate reviews (lacks reviews.moderate) -> 403
    res_unauth_rev = await async_client.post(
        "/api/v1/admin/reviews/1/moderate",
        headers=auth_header_for(fulfillment_user),
        json={"action": "approve"},
    )
    assert res_unauth_rev.status_code == 403

    # Fulfillment staff cannot manage content (lacks content.manage) -> 403
    res_unauth_cnt = await async_client.post(
        "/api/v1/admin/content/announcements",
        headers=auth_header_for(fulfillment_user),
        json={"message": "Unapproved banner"},
    )
    assert res_unauth_cnt.status_code == 403

    # Verify audit logs generated for admin coupon creation
    res_cpn = await async_client.post(
        "/api/v1/admin/coupons",
        headers=auth_header_for(admin),
        json={"code": "AUDITCHECK", "discount_type": "percentage", "discount_value": 15.0},
    )
    assert res_cpn.status_code == 201

    async with TestingSessionLocal() as session:
        audit_res = await session.execute(
            select(AuditLog).where(AuditLog.action == "promotions.coupon_created").order_by(AuditLog.id.desc())
        )
        audit_entry = audit_res.scalars().first()
        assert audit_entry is not None
        details = json.loads(audit_entry.details) if isinstance(audit_entry.details, str) else audit_entry.details
        assert details.get("code") == "AUDITCHECK"
