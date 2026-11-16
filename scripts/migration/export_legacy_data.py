#!/usr/bin/env python3
"""
Legacy Data Extraction Rehearsal
Extracts baseline seed data and domain structures into normalized JSON export files
for staging import reconciliation. Independent of SQLAlchemy runtime typing.
"""

import ast
import json
import os
import sys


def parse_python_constants(file_path, var_names):
    """Safely parse literal list/dict structures from Python source using AST."""
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)

    results = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in var_names:
                    try:
                        results[target.id] = ast.literal_eval(node.value)
                    except Exception as e:
                        print(f"Warning: could not literal_eval {target.id}: {e}")
    return results


def extract_legacy_data():
    print("=" * 70)
    print("Extracting Legacy UniNova Domain Data...")
    print("=" * 70)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    seed_file = os.path.join(repo_root, "backend", "app", "modules", "catalog", "seed_data.py")

    # Parse seed constants safely without triggering Python 3.14 SQLAlchemy ORM scan
    seed_constants = parse_python_constants(seed_file, ["SEED_CATEGORIES", "SEED_COLLECTIONS"])
    seed_categories = seed_constants.get("SEED_CATEGORIES", [])
    seed_collections = seed_constants.get("SEED_COLLECTIONS", [])

    # Permissions list definition
    permissions = [
        {"code": "dashboard.read", "display_name": "View Dashboard", "category": "dashboard"},
        {"code": "products.read", "display_name": "View Products", "category": "catalog"},
        {"code": "products.create", "display_name": "Create Products", "category": "catalog"},
        {"code": "products.update", "display_name": "Update Products", "category": "catalog"},
        {"code": "products.archive", "display_name": "Archive Products", "category": "catalog"},
        {"code": "products.publish", "display_name": "Publish Products", "category": "catalog"},
        {"code": "categories.manage", "display_name": "Manage Categories", "category": "catalog"},
        {"code": "collections.manage", "display_name": "Manage Collections", "category": "catalog"},
        {"code": "inventory.read", "display_name": "View Inventory", "category": "inventory"},
        {"code": "inventory.adjust", "display_name": "Adjust Inventory", "category": "inventory"},
        {"code": "orders.read", "display_name": "View Orders", "category": "orders"},
        {"code": "orders.update", "display_name": "Update Orders", "category": "orders"},
        {"code": "orders.cancel", "display_name": "Cancel Orders", "category": "orders"},
        {"code": "shipments.manage", "display_name": "Manage Shipments", "category": "fulfillment"},
        {"code": "customers.read", "display_name": "View Customers", "category": "customers"},
        {"code": "customers.update_status", "display_name": "Update Customer Status", "category": "customers"},
        {"code": "returns.read", "display_name": "View Returns", "category": "returns"},
        {"code": "returns.review", "display_name": "Review Returns", "category": "returns"},
        {"code": "returns.resolve", "display_name": "Resolve Returns", "category": "returns"},
        {"code": "payments.read", "display_name": "View Payments", "category": "payments"},
        {"code": "payments.reconcile", "display_name": "Reconcile Payments", "category": "payments"},
        {"code": "refunds.create", "display_name": "Create Refunds", "category": "payments"},
        {"code": "promotions.manage", "display_name": "Manage Promotions", "category": "marketing"},
        {"code": "reviews.moderate", "display_name": "Moderate Reviews", "category": "marketing"},
        {"code": "content.manage", "display_name": "Manage Content", "category": "marketing"},
        {"code": "staff.read", "display_name": "View Staff Directory", "category": "staff"},
        {"code": "staff.manage", "display_name": "Manage Staff Accounts", "category": "staff"},
        {"code": "roles.read", "display_name": "View Roles", "category": "rbac"},
        {"code": "roles.manage", "display_name": "Manage Roles", "category": "rbac"},
        {"code": "reports.read", "display_name": "View Reports", "category": "reports"},
        {"code": "reports.export", "display_name": "Export Reports", "category": "reports"},
        {"code": "settings.manage", "display_name": "Manage Settings", "category": "system"},
        {"code": "audit.read", "display_name": "View Audit Trail", "category": "system"},
    ]

    roles = [
        {"name": "store_admin", "display_name": "Store Administrator", "is_system": True},
        {"name": "catalog_manager", "display_name": "Catalog Manager", "is_system": True},
        {"name": "order_manager", "display_name": "Order Operations Manager", "is_system": True},
        {"name": "fulfillment_staff", "display_name": "Fulfillment & Dispatch Specialist", "is_system": True},
        {"name": "inventory_manager", "display_name": "Inventory Controller", "is_system": True},
        {"name": "support_staff", "display_name": "Customer Support Representative", "is_system": True},
        {"name": "customer", "display_name": "Storefront Customer", "is_system": True},
    ]

    export_payload = {
        "metadata": {
            "version": "1.0.0",
            "extracted_at": "2026-11-16T11:33:00Z",
            "source": "UniNova Serverful Pre-Migration Baseline",
        },
        "permissions": permissions,
        "roles": roles,
        "inventory_locations": [
            {
                "name": "Primary Fulfillment Center",
                "code": "WH-KHI-01",
                "address_line_1": "Korangi Industrial Area",
                "city": "Karachi",
                "postal_code": "74900",
                "country_code": "PK",
                "is_active": True,
            }
        ],
        "shipping_methods": [
            {
                "name": "Standard Delivery",
                "code": "standard",
                "base_rate": 350.00,
                "free_threshold": 5000.00,
                "estimated_days": "2-4 business days",
                "is_active": True,
            },
            {
                "name": "Express Courier Delivery",
                "code": "express",
                "base_rate": 650.00,
                "free_threshold": 10000.00,
                "estimated_days": "1-2 business days",
                "is_active": True,
            },
        ],
        "categories": seed_categories,
        "collections": seed_collections,
        "products": [
            {
                "name": "Relaxed Linen Overshirt",
                "slug": "relaxed-linen-overshirt",
                "category_slug": "men-jackets",
                "subtitle": "Pure washed French linen in sand stone",
                "description": "Cut for an easy, relaxed drape, this overshirt is crafted from breathable European linen.",
                "brand_label": "UniNova Atelier",
                "status": "active",
                "price": 8950.00,
                "original_price": 11500.00,
                "is_featured": True,
                "is_trending": True,
                "is_new_arrival": True,
                "variants": [
                    {
                        "sku": "SHIRT-LINEN-SAND-M",
                        "size": "M",
                        "color_name": "Sand Stone",
                        "color_hex": "#D2B48C",
                        "price": 8950.00,
                        "inventory_count": 25,
                    },
                    {
                        "sku": "SHIRT-LINEN-SAND-L",
                        "size": "L",
                        "color_name": "Sand Stone",
                        "color_hex": "#D2B48C",
                        "price": 8950.00,
                        "inventory_count": 30,
                    },
                ],
                "images": [
                    {
                        "image_url": "https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?q=80&w=1000&auto=format&fit=crop",
                        "alt_text": "Relaxed Linen Overshirt Front View",
                        "is_primary": True,
                    }
                ],
            },
            {
                "name": "Pleated Relaxed Trouser",
                "slug": "pleated-relaxed-trouser",
                "category_slug": "men-jeans-pants",
                "subtitle": "Italian cotton-twill with double forward pleats",
                "description": "A contemporary wide-leg silhouette featuring double pleats and side adjusters.",
                "brand_label": "UniNova Sartorial",
                "status": "active",
                "price": 12500.00,
                "original_price": 14500.00,
                "is_featured": True,
                "is_trending": False,
                "is_new_arrival": True,
                "variants": [
                    {
                        "sku": "TROUSER-TWILL-NAVY-32",
                        "size": "32",
                        "color_name": "Midnight Navy",
                        "color_hex": "#000080",
                        "price": 12500.00,
                        "inventory_count": 15,
                    }
                ],
                "images": [],
            },
            {
                "name": "Sculptural Drape Midi Dress",
                "slug": "sculptural-drape-midi-dress",
                "category_slug": "women",
                "subtitle": "Heavyweight mulberry silk in ivory",
                "description": "Fluid and architectural, this midi dress features an asymmetric cowl neckline.",
                "brand_label": "UniNova Atelier",
                "status": "active",
                "price": 18500.00,
                "original_price": None,
                "is_featured": True,
                "is_trending": True,
                "is_new_arrival": True,
                "variants": [
                    {
                        "sku": "DRESS-SILK-IVORY-S",
                        "size": "S",
                        "color_name": "Ivory",
                        "color_hex": "#FFFFF0",
                        "price": 18500.00,
                        "inventory_count": 12,
                    }
                ],
                "images": [
                    {
                        "image_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=1000&auto=format&fit=crop",
                        "alt_text": "Sculptural Drape Midi Dress Front View",
                        "is_primary": True,
                    }
                ],
            },
        ],
        "coupons": [
            {
                "code": "WELCOME10",
                "discount_type": "percentage",
                "discount_value": 10.00,
                "minimum_order_amount": 3000.00,
                "is_active": True,
            }
        ],
    }

    # Save to JSON
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "exports"))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "legacy_dataset.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2)

    print(f"Extraction successful!")
    print(f"Destination: {out_file}")
    print(f"Entities Extracted:")
    print(f"  - Permissions: {len(export_payload['permissions'])}")
    print(f"  - System Roles: {len(export_payload['roles'])}")
    print(f"  - Categories: {len(export_payload['categories'])}")
    print(f"  - Collections: {len(export_payload['collections'])}")
    print(f"  - Products: {len(export_payload['products'])}")
    total_variants = sum(len(p['variants']) for p in export_payload['products'])
    print(f"  - Variants: {total_variants}")
    print(f"  - Shipping Methods: {len(export_payload['shipping_methods'])}")
    print("=" * 70)


if __name__ == "__main__":
    extract_legacy_data()
