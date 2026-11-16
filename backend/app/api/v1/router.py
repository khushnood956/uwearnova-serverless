"""
API v1 Router Aggregator
Includes all v1 domain routers.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.cart.router import cart_router, wishlist_router
from app.modules.customer.router import admin_customers_router, customer_account_router
from app.modules.catalog.router import (
    admin_categories_router,
    admin_collections_router,
    admin_products_router,
    public_categories_router,
    public_collections_router,
    public_products_router,
)
from app.modules.fulfillment.router import (
    admin_fulfillment_router,
    customer_fulfillment_router,
    public_tracking_router,
)
from app.modules.inventory.router import admin_inventory_router
from app.modules.media.router import admin_media_router
from app.modules.orders.router import (
    admin_orders_router,
    customer_orders_router,
    public_orders_router,
)
from app.modules.payments.router import (
    admin_payments_router,
    customer_payments_router,
    public_payments_router,
)
from app.modules.returns.router import (
    admin_returns_router,
    customer_returns_router,
    public_returns_router,
)
from app.modules.rbac.router import router as rbac_router
from app.modules.shipping.router import admin_shipping_router, public_shipping_router
from app.modules.staff.router import staff_router
from app.modules.promotions.router import admin_promotions_router, public_promotions_router
from app.modules.reviews.router import admin_reviews_router, public_reviews_router
from app.modules.content.router import admin_content_router, public_content_router
from app.modules.reports.router import admin_reports_router
from app.modules.offline_sales.router import admin_offline_sales_router

api_v1_router = APIRouter()

# Health & Diagnostics
api_v1_router.include_router(health.router)

# Authentication & Identity
api_v1_router.include_router(auth_router)

# Storefront Catalog Navigation (Public)
api_v1_router.include_router(public_categories_router)
api_v1_router.include_router(public_collections_router)
api_v1_router.include_router(public_products_router)

# Storefront Commerce (Cart & Wishlist & Shipping & Orders & Payments & Tracking & Returns & Promotions & Reviews & Content)
api_v1_router.include_router(cart_router)
api_v1_router.include_router(wishlist_router)
api_v1_router.include_router(public_shipping_router)
api_v1_router.include_router(public_orders_router)
api_v1_router.include_router(public_tracking_router)
api_v1_router.include_router(public_returns_router)
api_v1_router.include_router(public_payments_router)
api_v1_router.include_router(public_promotions_router)
api_v1_router.include_router(public_reviews_router)
api_v1_router.include_router(public_content_router)

# Customer Portal
api_v1_router.include_router(customer_account_router)
api_v1_router.include_router(customer_orders_router)
api_v1_router.include_router(customer_fulfillment_router)
api_v1_router.include_router(customer_returns_router)
api_v1_router.include_router(customer_payments_router)

# Roles & Access Control (Admin)
api_v1_router.include_router(rbac_router)

# Audit Trail (Admin)
api_v1_router.include_router(audit_router)

# Catalog Management (Admin)
api_v1_router.include_router(admin_categories_router)
api_v1_router.include_router(admin_collections_router)
api_v1_router.include_router(admin_products_router)
api_v1_router.include_router(admin_media_router)

# Inventory Management (Admin)
api_v1_router.include_router(admin_inventory_router)

# Shipping Management (Admin)
api_v1_router.include_router(admin_shipping_router)

# Customer Management (Admin)
api_v1_router.include_router(admin_customers_router)

# Order & Payment & Fulfillment & Returns Operations (Admin)
api_v1_router.include_router(admin_orders_router)
api_v1_router.include_router(admin_payments_router)
api_v1_router.include_router(admin_fulfillment_router)
api_v1_router.include_router(admin_returns_router)

# Staff Operations & Work Queues (Module M20)
api_v1_router.include_router(staff_router)

# Promotions, Reviews, and Content Management (Module M21)
api_v1_router.include_router(admin_promotions_router)
api_v1_router.include_router(admin_reviews_router)
api_v1_router.include_router(admin_content_router)

# Store Reporting & Analytics (Module M22)
api_v1_router.include_router(admin_reports_router)

# Offline Sales & POS Walk-in Transactions
api_v1_router.include_router(admin_offline_sales_router)
