"""
Standard Permissions and Role Definitions
Derived strictly from docs/backend/03-dashboards-and-rbac.md.
"""

from typing import Dict, List, NamedTuple


class PermissionDef(NamedTuple):
    code: str
    description: str
    category: str


# Complete inventory of UniNova system permissions
ALL_PERMISSIONS: List[PermissionDef] = [
    # Dashboard Overview
    PermissionDef("dashboard.read", "View operational dashboard metrics and summaries", "dashboard"),

    # Catalog & Products
    PermissionDef("products.read", "View product catalog, variants, and stock levels", "catalog"),
    PermissionDef("products.create", "Create new product drafts and variants", "catalog"),
    PermissionDef("products.update", "Edit product details, pricing, and descriptions", "catalog"),
    PermissionDef("products.archive", "Archive or unpublish products", "catalog"),
    PermissionDef("products.publish", "Publish drafts to live customer storefront", "catalog"),
    PermissionDef("categories.manage", "Create, edit, and organize product categories", "catalog"),
    PermissionDef("collections.manage", "Curate and organize seasonal collections", "catalog"),

    # Inventory
    PermissionDef("inventory.read", "Inspect stock counts across variants and locations", "inventory"),
    PermissionDef("inventory.adjust", "Execute manual stock adjustments with audit reasons", "inventory"),

    # Orders & Fulfillment
    PermissionDef("orders.read", "Search, view, and inspect customer orders", "orders"),
    PermissionDef("orders.update", "Update order workflow and fulfillment states", "orders"),
    PermissionDef("orders.cancel", "Cancel unfulfilled orders within policy", "orders"),
    PermissionDef("shipments.manage", "Assign couriers, generate consignments, and update tracking", "fulfillment"),

    # Customers
    PermissionDef("customers.read", "View customer profiles and order histories", "customers"),
    PermissionDef("customers.update_status", "Disable or modify customer account status", "customers"),

    # Returns & Exchanges
    PermissionDef("returns.read", "View doorstep exchange and return requests", "returns"),
    PermissionDef("returns.review", "Inspect returned garments and assess condition", "returns"),
    PermissionDef("returns.resolve", "Approve or reject exchanges and trigger replacement dispatch", "returns"),

    # Payments & Reconciliation
    PermissionDef("payments.read", "View payment statuses and transaction logs", "payments"),
    PermissionDef("payments.reconcile", "Mark COD deliveries collected and reconcile courier settlements", "payments"),
    PermissionDef("refunds.create", "Approve and execute payment refunds", "payments"),

    # Marketing & Reviews
    PermissionDef("promotions.manage", "Configure discount coupons and promotional campaigns", "marketing"),
    PermissionDef("reviews.moderate", "Approve or hide customer product reviews", "marketing"),
    PermissionDef("content.manage", "Manage homepage banners and editorial content", "marketing"),

    # Staff & RBAC
    PermissionDef("staff.read", "View staff directory and operational assignments", "staff"),
    PermissionDef("staff.manage", "Create and modify staff accounts", "staff"),
    PermissionDef("roles.read", "Inspect available system roles and assigned permissions", "rbac"),
    PermissionDef("roles.manage", "Assign and modify staff roles", "rbac"),

    # Reporting & System
    PermissionDef("reports.read", "Access sales, inventory, and performance reports", "reports"),
    PermissionDef("reports.export", "Export sensitive analytical and operational data", "reports"),
    PermissionDef("settings.manage", "Modify store configurations, shipping rules, and policies", "system"),
    PermissionDef("audit.read", "Inspect the full administrative audit trail", "system"),
]

# Standard Role to Permission Mappings
SYSTEM_ROLES: Dict[str, Dict[str, any]] = {
    "store_admin": {
        "display_name": "Store Administrator",
        "description": "Full access to all administrative, catalog, financial, and security capabilities.",
        "permissions": [p.code for p in ALL_PERMISSIONS],
    },
    "order_manager": {
        "display_name": "Order Operations Manager",
        "description": "Manages order processing, customer confirmations, and cancellations.",
        "permissions": [
            "dashboard.read",
            "orders.read",
            "orders.update",
            "orders.cancel",
            "customers.read",
            "returns.read",
        ],
    },
    "fulfillment_staff": {
        "display_name": "Fulfillment & Dispatch Specialist",
        "description": "Picks, packs, and dispatches parcels and manages courier shipments.",
        "permissions": [
            "dashboard.read",
            "orders.read",
            "shipments.manage",
        ],
    },
    "inventory_manager": {
        "display_name": "Inventory Controller",
        "description": "Receives stock, adjusts variant quantities with reason, and monitors thresholds.",
        "permissions": [
            "dashboard.read",
            "products.read",
            "inventory.read",
            "inventory.adjust",
        ],
    },
    "customer_support": {
        "display_name": "Customer Care & Styling Concierge",
        "description": "Assists clients with sizing inquiries, orders, and doorstep exchange requests.",
        "permissions": [
            "dashboard.read",
            "orders.read",
            "customers.read",
            "returns.read",
            "returns.review",
            "returns.resolve",
        ],
    },
    "catalog_editor": {
        "display_name": "Catalog & Content Editor",
        "description": "Edits product copy, imagery, categories, and curated collections; cannot modify security, payments, or orders.",
        "permissions": [
            "dashboard.read",
            "products.read",
            "products.create",
            "products.update",
            "categories.manage",
            "collections.manage",
            "content.manage",
        ],
    },
    "finance_operator": {
        "display_name": "Finance & Payments Operator",
        "description": "Monitors payment gateways, reconciles COD courier remittances, and processes authorized refunds.",
        "permissions": [
            "dashboard.read",
            "orders.read",
            "payments.read",
            "payments.reconcile",
            "refunds.create",
        ],
    },
    "customer": {
        "display_name": "Registered Customer",
        "description": "Access to customer account portal, personal order history, and saved wishlist.",
        "permissions": [],
    },
}
