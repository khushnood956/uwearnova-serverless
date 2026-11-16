"""
Catalog Seeder
Loads the authentic UniNova categories, collections, and department hierarchy
(Men, Women, Kids and future Coming Soon departments) along with baseline administrative accounts.
"""

from decimal import Decimal
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.models  # noqa: F401 - Register domain models in Base.metadata
from app.modules.catalog.models import Category, Collection, Product, ProductImage, ProductVariant


SEED_CATEGORIES = [
    # --- ROOT DEPARTMENTS ---
    {
        "name": "Men",
        "slug": "men",
        "description": "Structured blazers, refined linen shirts, tailored trousers, and elevated knitwear.",
        "image_url": "https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?q=80&w=1000&auto=format&fit=crop",
        "sort_order": 1,
        "is_coming_soon": False,
        "parent_slug": None,
    },
    {
        "name": "Women",
        "slug": "women",
        "description": "Fluid silhouettes, tailored separates, sculptural dresses, and fine cashmere knits.",
        "image_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=1000&auto=format&fit=crop",
        "sort_order": 2,
        "is_coming_soon": False,
        "parent_slug": None,
    },
    {
        "name": "Kids",
        "slug": "kids",
        "description": "Comfortable, premium cotton staples and warm fleece knitwear for children.",
        "image_url": "https://images.unsplash.com/photo-1503944583220-79d8926ad5e2?q=80&w=1000&auto=format&fit=crop",
        "sort_order": 3,
        "is_coming_soon": False,
        "parent_slug": None,
    },
    # --- FUTURE DEPARTMENTS (COMING SOON) ---
    {
        "name": "Footwear",
        "slug": "footwear",
        "description": "Handcrafted calfskin loafers, minimalist derbies, and modern court sneakers. More to explore. New collections are coming soon.",
        "image_url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?q=80&w=1000&auto=format&fit=crop",
        "sort_order": 4,
        "is_coming_soon": True,
        "parent_slug": None,
    },
    {
        "name": "Accessories",
        "slug": "accessories",
        "description": "Architectural leather totes, minimal belts, and signature silk scarves. More to explore. New collections are coming soon.",
        "image_url": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?q=80&w=1000&auto=format&fit=crop",
        "sort_order": 5,
        "is_coming_soon": True,
        "parent_slug": None,
    },
    {
        "name": "Perfumes",
        "slug": "perfumes",
        "description": "Niche extrait de parfum, botanical accords, and subtle luxury fragrances. More to explore. New collections are coming soon.",
        "image_url": "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?q=80&w=1000&auto=format&fit=crop",
        "sort_order": 6,
        "is_coming_soon": True,
        "parent_slug": None,
    },

    # --- MEN SUBCATEGORIES ---
    {"name": "Men's Hoodies", "slug": "men-hoodies", "description": "Heavyweight cotton-fleece hoodies and casual pullovers.", "sort_order": 1, "is_coming_soon": False, "parent_slug": "men"},
    {"name": "Men's Jackets", "slug": "men-jackets", "description": "Structured wool blazers, overshirts, and architectural trench coats.", "sort_order": 2, "is_coming_soon": False, "parent_slug": "men"},
    {"name": "Men's T-Shirts", "slug": "men-t-shirts", "description": "Fine-combed pima cotton crewnecks and mandarin collar shirting.", "sort_order": 3, "is_coming_soon": False, "parent_slug": "men"},
    {"name": "Men's Sweaters", "slug": "men-sweaters", "description": "Extra-fine merino wool and Mongolian cashmere knitwear.", "sort_order": 4, "is_coming_soon": False, "parent_slug": "men"},
    {"name": "Men's Jeans & Pants", "slug": "men-jeans-pants", "description": "Double-pleat tailored trousers and Japanese raw denim.", "sort_order": 5, "is_coming_soon": False, "parent_slug": "men"},

    # --- WOMEN SUBCATEGORIES ---
    {"name": "Women's Hoodies", "slug": "women-hoodies", "description": "Relaxed-fit cropped hoodies and soft modal pullovers.", "sort_order": 1, "is_coming_soon": False, "parent_slug": "women"},
    {"name": "Women's Jackets", "slug": "women-jackets", "description": "Tailored outerwear, raw silk trenches, and cape coats.", "sort_order": 2, "is_coming_soon": False, "parent_slug": "women"},
    {"name": "Women's T-Shirts", "slug": "women-t-shirts", "description": "Silk-cotton blend tops and minimal crewneck essentials.", "sort_order": 3, "is_coming_soon": False, "parent_slug": "women"},
    {"name": "Women's Sweaters", "slug": "women-sweaters", "description": "Ribbed cashmere knit tops and fine drape cardigans.", "sort_order": 4, "is_coming_soon": False, "parent_slug": "women"},

    # --- KIDS SUBCATEGORIES ---
    {"name": "Kids' Hoodies", "slug": "kids-hoodies", "description": "Warm, durable cotton fleece hoodies for kids.", "sort_order": 1, "is_coming_soon": False, "parent_slug": "kids"},
    {"name": "Kids' Jackets", "slug": "kids-jackets", "description": "Cozy outerwear and light zip-up jackets.", "sort_order": 2, "is_coming_soon": False, "parent_slug": "kids"},
    {"name": "Kids' T-Shirts", "slug": "kids-t-shirts", "description": "Breathable 100% organic cotton everyday tees.", "sort_order": 3, "is_coming_soon": False, "parent_slug": "kids"},
    {"name": "Kids' Sweaters", "slug": "kids-sweaters", "description": "Soft knit crewnecks and cozy cardigans.", "sort_order": 4, "is_coming_soon": False, "parent_slug": "kids"},
]

SEED_COLLECTIONS = [
    {"name": "New Arrivals", "slug": "new-arrivals", "description": "Latest seasonal runway drops.", "sort_order": 1},
    {"name": "Essentials", "slug": "essentials", "description": "Timeless luxury wardrobe staples.", "sort_order": 2},
    {"name": "Signature Collection", "slug": "signature", "description": "Refined architectural statement pieces.", "sort_order": 3},
    {"name": "Trending Pieces", "slug": "trending", "description": "Most sought-after seasonal garments.", "sort_order": 4},
    {"name": "Curated Archive Sale", "slug": "sale", "description": "Limited archive offerings.", "sort_order": 5},
]

# Sample products used strictly for test suite verification
SAMPLE_TEST_PRODUCTS = [
    {
        "slug": "monolith-oversized-wool-blazer",
        "name": "Monolith Oversized Blazer",
        "subtitle": "Heavyweight Virgin Wool Blend",
        "description": "Crafted with a relaxed architectural shoulder and unstructured drape. Featuring peak lapels, tonal horn buttons, and internal silk-blend lining.",
        "category_slug": "men-jackets",
        "collection_slugs": ["signature", "trending", "new-arrivals"],
        "price": Decimal("24500.00"),
        "original_price": Decimal("28000.00"),
        "is_new_arrival": True,
        "is_trending": True,
        "is_featured": True,
        "fabric_care": '["70% Virgin Wool, 30% Mulberry Silk", "Specialist dry clean only", "Cool iron with pressing cloth"]',
        "delivery_notes": "Ships within 24 hours. Free express delivery in Pakistan.",
        "rating": Decimal("4.9"),
        "review_count": 18,
        "images": [
            "https://images.unsplash.com/photo-1507679799987-c73779587ccf?q=80&w=1000&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "BLZ-BLK-38", "size": "38R", "color_name": "Obsidian Black", "color_hex": "#111111", "inventory_count": 5, "in_stock": True},
            {"sku": "BLZ-BLK-40", "size": "40R", "color_name": "Obsidian Black", "color_hex": "#111111", "inventory_count": 8, "in_stock": True},
            {"sku": "BLZ-BLK-42", "size": "42R", "color_name": "Obsidian Black", "color_hex": "#111111", "inventory_count": 3, "in_stock": True},
            {"sku": "BLZ-SND-40", "size": "40R", "color_name": "Sand Ivory", "color_hex": "#F2F0EB", "inventory_count": 4, "in_stock": True},
        ],
    },
    {
        "slug": "relaxed-egyptian-cotton-kurta-shirt",
        "name": "Relaxed Linen-Cotton Shirt",
        "subtitle": "Hand-spun breathable weave",
        "description": "A contemporary crossover of classic tailored shirting and subcontinental ease. Features a clean mandarin collar and concealed placket.",
        "category_slug": "men-t-shirts",
        "collection_slugs": ["essentials", "trending"],
        "price": Decimal("8900.00"),
        "is_new_arrival": False,
        "is_trending": True,
        "is_featured": True,
        "fabric_care": '["100% Giza Egyptian Cotton", "Machine wash gentle cycle cold", "Warm iron while slightly damp"]',
        "rating": Decimal("4.8"),
        "review_count": 34,
        "images": [
            "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "SHT-WHT-S", "size": "S", "color_name": "Warm Ivory", "color_hex": "#F5F3EE", "inventory_count": 12, "in_stock": True},
            {"sku": "SHT-WHT-M", "size": "M", "color_name": "Warm Ivory", "color_hex": "#F5F3EE", "inventory_count": 15, "in_stock": True},
            {"sku": "SHT-WHT-L", "size": "L", "color_name": "Warm Ivory", "color_hex": "#F5F3EE", "inventory_count": 9, "in_stock": True},
            {"sku": "SHT-NVY-M", "size": "M", "color_name": "Midnight Slate", "color_hex": "#222831", "inventory_count": 7, "in_stock": True},
        ],
    },
    {
        "slug": "pleated-wide-leg-trousers",
        "name": "Tailored Pleated Trousers",
        "subtitle": "High-waist double pleat cut",
        "description": "Architectural wide trousers with double forward pleats, side adjusters, and deep welt pockets. Pairs seamlessly with tailored blazers or fine knitwear.",
        "category_slug": "men-jeans-pants",
        "collection_slugs": ["essentials", "signature"],
        "price": Decimal("13500.00"),
        "is_new_arrival": True,
        "is_trending": False,
        "is_featured": True,
        "rating": Decimal("4.7"),
        "review_count": 12,
        "images": [
            "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?q=80&w=1000&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1479064555552-3ef4979f8908?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "TRS-CHR-30", "size": "30", "color_name": "Charcoal", "color_hex": "#333333", "inventory_count": 6, "in_stock": True},
            {"sku": "TRS-CHR-32", "size": "32", "color_name": "Charcoal", "color_hex": "#333333", "inventory_count": 11, "in_stock": True},
            {"sku": "TRS-CHR-34", "size": "34", "color_name": "Charcoal", "color_hex": "#333333", "inventory_count": 4, "in_stock": True},
        ],
    },
    {
        "slug": "sculptural-wrap-midi-dress",
        "name": "Sculptural Wrap Midi Dress",
        "subtitle": "Fluid Japanese Crepe",
        "description": "A versatile silhouette featuring asymmetrical draping, elongated cuff detailing, and an adjustable self-tie sash.",
        "category_slug": "women-jackets",
        "collection_slugs": ["signature", "trending", "new-arrivals"],
        "price": Decimal("21900.00"),
        "original_price": Decimal("25500.00"),
        "is_new_arrival": True,
        "is_trending": True,
        "is_featured": True,
        "fabric_care": '["95% Japanese Poly-Crepe, 5% Elastane", "Dry clean or hand wash delicate", "Steam iron recommended"]',
        "rating": Decimal("5.0"),
        "review_count": 22,
        "images": [
            "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?q=80&w=1000&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "DRS-BLK-XS", "size": "XS", "color_name": "Obsidian", "color_hex": "#111111", "inventory_count": 4, "in_stock": True},
            {"sku": "DRS-BLK-S", "size": "S", "color_name": "Obsidian", "color_hex": "#111111", "inventory_count": 9, "in_stock": True},
            {"sku": "DRS-BLK-M", "size": "M", "color_name": "Obsidian", "color_hex": "#111111", "inventory_count": 7, "in_stock": True},
            {"sku": "DRS-CHP-S", "size": "S", "color_name": "Champagne", "color_hex": "#C5AA82", "inventory_count": 3, "in_stock": True},
        ],
    },
    {
        "slug": "raw-silk-trench-cape",
        "name": "Minimalist Silk-Blend Trench",
        "subtitle": "Lightweight layering outerwear",
        "description": "Clean-lined statement outerwear finished with storm flaps, raglan sleeves, and deep side slits for fluid movement.",
        "category_slug": "women-jackets",
        "collection_slugs": ["signature", "new-arrivals"],
        "price": Decimal("29500.00"),
        "is_new_arrival": True,
        "is_trending": False,
        "is_featured": True,
        "rating": Decimal("4.9"),
        "review_count": 15,
        "images": [
            "https://images.unsplash.com/photo-1548624149-f9b1859aa9d0?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "TRN-TAU-S", "size": "S/M", "color_name": "Warm Taupe", "color_hex": "#C5AA82", "inventory_count": 6, "in_stock": True},
            {"sku": "TRN-TAU-L", "size": "L/XL", "color_name": "Warm Taupe", "color_hex": "#C5AA82", "inventory_count": 4, "in_stock": True},
        ],
    },
    {
        "slug": "fine-ribbed-cashmere-knit-top",
        "name": "Fine Ribbed Knit Top",
        "subtitle": "Ultra-fine Mongolian Cashmere Blend",
        "description": "A buttery soft foundation layer featuring a gentle crew neck, extended sleeves, and delicate ribbed hems.",
        "category_slug": "women-sweaters",
        "collection_slugs": ["essentials", "trending"],
        "price": Decimal("11500.00"),
        "is_new_arrival": False,
        "is_trending": True,
        "is_featured": True,
        "rating": Decimal("4.8"),
        "review_count": 41,
        "images": [
            "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "KNT-IVO-S", "size": "S", "color_name": "Ivory Light", "color_hex": "#F5F3EE", "inventory_count": 14, "in_stock": True},
            {"sku": "KNT-IVO-M", "size": "M", "color_name": "Ivory Light", "color_hex": "#F5F3EE", "inventory_count": 10, "in_stock": True},
            {"sku": "KNT-IVO-L", "size": "L", "color_name": "Ivory Light", "color_hex": "#F5F3EE", "inventory_count": 0, "in_stock": False},
        ],
    },
    {
        "slug": "artisan-calfskin-penny-loafer",
        "name": "Artisan Penny Loafer",
        "subtitle": "Full-grain calfskin leather",
        "description": "Hand-lasted penny loafer with Blake-stitched leather soles, stacked heel, and memory-foam cushioned footbed.",
        "category_slug": "footwear",
        "collection_slugs": ["signature", "trending", "new-arrivals"],
        "price": Decimal("18500.00"),
        "is_new_arrival": True,
        "is_trending": True,
        "is_featured": True,
        "rating": Decimal("4.9"),
        "review_count": 29,
        "images": [
            "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?q=80&w=1000&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1549298916-b41d501d3772?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "LFR-BLK-40", "size": "40", "color_name": "Polished Black", "color_hex": "#111111", "inventory_count": 5, "in_stock": True},
            {"sku": "LFR-BLK-41", "size": "41", "color_name": "Polished Black", "color_hex": "#111111", "inventory_count": 7, "in_stock": True},
        ],
    },
    {
        "slug": "minimalist-leather-court-sneaker",
        "name": "Minimalist Court Sneaker",
        "subtitle": "Italian Napa leather upper",
        "description": "A pristine low-profile court sneaker devoid of exterior logos. Finished with waxed cotton laces and Margom-style cupsole.",
        "category_slug": "footwear",
        "collection_slugs": ["essentials", "trending"],
        "price": Decimal("14900.00"),
        "original_price": Decimal("17500.00"),
        "is_new_arrival": False,
        "is_trending": True,
        "is_featured": True,
        "rating": Decimal("4.8"),
        "review_count": 53,
        "images": [
            "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?q=80&w=1000&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1560769629-975ec94e6a86?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "SNK-WHT-41", "size": "41", "color_name": "Pure Chalk", "color_hex": "#FFFFFF", "inventory_count": 10, "in_stock": True},
            {"sku": "SNK-WHT-42", "size": "42", "color_name": "Pure Chalk", "color_hex": "#FFFFFF", "inventory_count": 12, "in_stock": True},
            {"sku": "SNK-WHT-43", "size": "43", "color_name": "Pure Chalk", "color_hex": "#FFFFFF", "inventory_count": 6, "in_stock": True},
        ],
    },
    {
        "slug": "architectural-leather-tote",
        "name": "Architectural Leather Tote",
        "subtitle": "Vegetable-tanned full grain",
        "description": "Structured everyday tote with magnetic closure, interior zippered laptop partition, and reinforced tubular handles.",
        "category_slug": "accessories",
        "collection_slugs": ["signature", "trending", "new-arrivals"],
        "price": Decimal("19800.00"),
        "is_new_arrival": True,
        "is_trending": True,
        "is_featured": True,
        "rating": Decimal("4.9"),
        "review_count": 37,
        "images": [
            "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?q=80&w=1000&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1584917865442-de89df76afd3?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "BAG-BLK-OS", "size": "One Size", "color_name": "Obsidian", "color_hex": "#111111", "inventory_count": 8, "in_stock": True},
            {"sku": "BAG-COG-OS", "size": "One Size", "color_name": "Rich Cognac", "color_hex": "#A68960", "inventory_count": 5, "in_stock": True},
        ],
    },
    {
        "slug": "pure-silk-twill-scarf",
        "name": "Pure Silk Twill Scarf",
        "subtitle": "Hand-rolled French hem",
        "description": "Square silk scarf adorned with subtle geometric line work inspired by Pakistani architectural heritage.",
        "category_slug": "accessories",
        "collection_slugs": ["essentials", "signature"],
        "price": Decimal("6800.00"),
        "is_new_arrival": False,
        "is_trending": False,
        "is_featured": True,
        "rating": Decimal("4.9"),
        "review_count": 19,
        "images": [
            "https://images.unsplash.com/photo-1601924994987-69e26d50dc26?q=80&w=1000&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1584030373081-f37b7bb4fa8e?q=80&w=1000&auto=format&fit=crop",
        ],
        "variants": [
            {"sku": "SCF-GLD-OS", "size": "90x90 cm", "color_name": "Champagne / Obsidian", "color_hex": "#C5AA82", "inventory_count": 15, "in_stock": True},
        ],
    },
]


async def seed_catalog_products(db: AsyncSession, include_products: Optional[bool] = None) -> None:
    """
    Ensure all authentic categories, collections, and hierarchy exist in database.
    If include_products is False, existing dummy products are deleted and no products are seeded.
    If include_products is True, test sample products are seeded.
    Defaults to True only when APP_ENV == 'test'.
    """
    from app.core.config import get_settings
    settings = get_settings()

    import os
    if include_products is None:
        include_products = (settings.APP_ENV == "test" or "PYTEST_CURRENT_TEST" in os.environ)

    # 1. Seed Root Categories
    existing_cats_res = await db.execute(select(Category))
    cat_by_slug = {c.slug: c for c in existing_cats_res.scalars().all()}

    root_categories = [c for c in SEED_CATEGORIES if c.get("parent_slug") is None]
    for cat_data in root_categories:
        if cat_data["slug"] in cat_by_slug:
            cat = cat_by_slug[cat_data["slug"]]
            cat.name = cat_data["name"]
            cat.description = cat_data["description"]
            cat.is_coming_soon = cat_data.get("is_coming_soon", False)
            cat.is_active = True
        else:
            cat = Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                description=cat_data["description"],
                image_url=cat_data.get("image_url"),
                sort_order=cat_data["sort_order"],
                is_active=True,
                is_coming_soon=cat_data.get("is_coming_soon", False),
                parent_id=None,
            )
            db.add(cat)
            await db.flush()
            cat_by_slug[cat.slug] = cat

    # 2. Seed Subcategories with Parent IDs
    sub_categories = [c for c in SEED_CATEGORIES if c.get("parent_slug") is not None]
    for cat_data in sub_categories:
        parent = cat_by_slug.get(cat_data["parent_slug"])
        parent_id = parent.id if parent else None

        if cat_data["slug"] in cat_by_slug:
            cat = cat_by_slug[cat_data["slug"]]
            cat.name = cat_data["name"]
            cat.description = cat_data["description"]
            cat.parent_id = parent_id
            cat.is_coming_soon = cat_data.get("is_coming_soon", False)
            cat.is_active = True
        else:
            cat = Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                description=cat_data["description"],
                image_url=cat_data.get("image_url"),
                sort_order=cat_data["sort_order"],
                is_active=True,
                is_coming_soon=cat_data.get("is_coming_soon", False),
                parent_id=parent_id,
            )
            db.add(cat)
            await db.flush()
            cat_by_slug[cat.slug] = cat

    # 3. Seed Collections
    existing_cols_res = await db.execute(select(Collection))
    col_by_slug = {c.slug: c for c in existing_cols_res.scalars().all()}

    for col_data in SEED_COLLECTIONS:
        if col_data["slug"] not in col_by_slug:
            col = Collection(
                name=col_data["name"],
                slug=col_data["slug"],
                description=col_data["description"],
                sort_order=col_data["sort_order"],
                is_active=True,
            )
            db.add(col)
            await db.flush()
            col_by_slug[col.slug] = col

    # 4. Clean or Seed Products
    if not include_products:
        # Keep existing products intact (do not delete user/admin products)
        pass
    else:
        existing_prods_res = await db.execute(select(Product))
        prod_by_slug = {p.slug: p for p in existing_prods_res.scalars().all()}

        for p_data in SAMPLE_TEST_PRODUCTS:
            if p_data["slug"] in prod_by_slug:
                continue

            target_cat = cat_by_slug.get(p_data["category_slug"])
            if not target_cat:
                continue
            target_cols = [col_by_slug[c_slug] for c_slug in p_data["collection_slugs"] if c_slug in col_by_slug]

            product = Product(
                name=p_data["name"],
                slug=p_data["slug"],
                subtitle=p_data["subtitle"],
                description=p_data["description"],
                category_id=target_cat.id,
                brand_label="UWEARNOVA",
                status="active",
                price=p_data["price"],
                original_price=p_data.get("original_price"),
                is_new_arrival=p_data["is_new_arrival"],
                is_trending=p_data["is_trending"],
                is_featured=p_data["is_featured"],
                fabric_care=p_data.get("fabric_care"),
                delivery_notes=p_data.get("delivery_notes"),
                rating=p_data["rating"],
                review_count=p_data["review_count"],
                collections=target_cols,
                variants=[],
                images=[],
            )

            for idx, img_url in enumerate(p_data["images"]):
                product.images.append(
                    ProductImage(
                        image_url=img_url,
                        sort_order=idx,
                        is_primary=(idx == 0),
                    )
                )

            for v_data in p_data["variants"]:
                product.variants.append(
                    ProductVariant(
                        sku=v_data["sku"],
                        size=v_data["size"],
                        color_name=v_data["color_name"],
                        color_hex=v_data["color_hex"],
                        inventory_count=v_data["inventory_count"],
                        in_stock=v_data["in_stock"],
                        is_active=True,
                    )
                )

            db.add(product)
            prod_by_slug[product.slug] = product

    await db.flush()


seed_catalog_data = seed_catalog_products


async def wipe_all_products(db: AsyncSession) -> None:
    """Safely wipe all existing products, variants, images, inventory, and sales records."""
    from sqlalchemy import text
    
    # Delete child dependencies in foreign-key order
    tables_to_clear = [
        "offline_sale_items",
        "offline_sales",
        "return_items",
        "order_items",
        "cart_items",
        "wishlist_items",
        "product_reviews",
        "inventory_movements",
        "inventory_items",
        "product_collections",
        "product_images",
        "product_variants",
        "products",
    ]
    for table in tables_to_clear:
        await db.execute(text(f"DELETE FROM {table}"))
    await db.flush()


async def seed_default_locations(db: AsyncSession) -> None:
    """Ensure default fulfillment center location in Sialkot, Pakistan exists."""
    from app.modules.inventory.models import InventoryLocation

    loc_res = await db.execute(select(InventoryLocation).where(InventoryLocation.code == "SKT-FC1"))
    location = loc_res.scalar_one_or_none()
    if not location:
        location = InventoryLocation(
            name="Sialkot Central Fulfillment Center",
            code="SKT-FC1",
            address_line_1="Paris Road, Cantt",
            city="Sialkot",
            country_code="PK",
            is_active=True,
        )
        db.add(location)
        await db.flush()
    else:
        location.name = "Sialkot Central Fulfillment Center"
        location.city = "Sialkot"
        location.address_line_1 = "Paris Road, Cantt"
        location.is_active = True
        await db.flush()


async def purge_legacy_uninova_accounts(db: AsyncSession) -> None:
    """Purge all legacy @uninova accounts and associated data."""
    from sqlalchemy import text
    
    # Remove user_roles, staff_profiles, customer_profiles for @uninova accounts
    await db.execute(text("""
        DELETE FROM user_roles WHERE user_id IN (
            SELECT id FROM users WHERE email LIKE '%@uninova%'
        )
    """))
    await db.execute(text("""
        DELETE FROM staff_profiles WHERE user_id IN (
            SELECT id FROM users WHERE email LIKE '%@uninova%'
        )
    """))
    await db.execute(text("""
        DELETE FROM customer_profiles WHERE user_id IN (
            SELECT id FROM users WHERE email LIKE '%@uninova%'
        )
    """))
    await db.execute(text("""
        DELETE FROM refresh_tokens WHERE user_id IN (
            SELECT id FROM users WHERE email LIKE '%@uninova%'
        )
    """))
    await db.execute(text("DELETE FROM users WHERE email LIKE '%@uninova%'"))
    await db.flush()


async def seed_default_users(db: AsyncSession) -> None:
    """Ensure baseline admin, staff, and customer accounts exist and are ready for login."""
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.customer.models import CustomerProfile
    from app.modules.rbac.models import Role, user_roles
    from app.modules.staff.models import StaffProfile

    # Map of roles
    role_res = await db.execute(select(Role))
    roles_by_name = {r.name: r for r in role_res.scalars().all()}

    async def upsert_user(
        email: str,
        password: str,
        user_type: str,
        role_name: Optional[str] = None,
        staff_meta: Optional[dict] = None,
        customer_meta: Optional[dict] = None,
    ) -> User:
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                password_hash=hash_password(password),
                phone=customer_meta.get("phone") if customer_meta else None,
                user_type=user_type,
                status="active",
            )
            db.add(user)
            await db.flush()
        else:
            user.password_hash = hash_password(password)
            user.user_type = user_type
            user.status = "active"
            if customer_meta and customer_meta.get("phone"):
                user.phone = customer_meta["phone"]
            user.failed_login_attempts = 0
            user.locked_until = None
            await db.flush()

        # Assign Role
        if role_name and role_name in roles_by_name:
            target_role = roles_by_name[role_name]
            existing_ur = await db.execute(
                select(user_roles).where(
                    user_roles.c.user_id == user.id,
                    user_roles.c.role_id == target_role.id,
                )
            )
            if not existing_ur.first():
                await db.execute(
                    user_roles.insert().values(user_id=user.id, role_id=target_role.id)
                )

        # Upsert Staff Profile
        if staff_meta:
            sp_res = await db.execute(select(StaffProfile).where(StaffProfile.user_id == user.id))
            staff_profile = sp_res.scalar_one_or_none()
            if not staff_profile:
                # Check if employee_code is taken by someone else
                code_res = await db.execute(select(StaffProfile).where(StaffProfile.employee_code == staff_meta["employee_code"]))
                existing_code_sp = code_res.scalar_one_or_none()
                if existing_code_sp:
                    existing_code_sp.employee_code = f"{existing_code_sp.employee_code}_OLD_{existing_code_sp.user_id}"
                    await db.flush()

                staff_profile = StaffProfile(
                    user_id=user.id,
                    employee_code=staff_meta["employee_code"],
                    department=staff_meta["department"],
                    job_title=staff_meta["job_title"],
                    is_active=True,
                )
                db.add(staff_profile)
            else:
                staff_profile.employee_code = staff_meta["employee_code"]
                staff_profile.department = staff_meta["department"]
                staff_profile.job_title = staff_meta["job_title"]
                staff_profile.is_active = True
            await db.flush()

        # Upsert Customer Profile
        if customer_meta:
            cp_res = await db.execute(select(CustomerProfile).where(CustomerProfile.user_id == user.id))
            customer_profile = cp_res.scalar_one_or_none()
            if not customer_profile:
                customer_profile = CustomerProfile(
                    user_id=user.id,
                    first_name=customer_meta.get("first_name", "Valued"),
                    last_name=customer_meta.get("last_name", "Customer"),
                )
                db.add(customer_profile)
            else:
                customer_profile.first_name = customer_meta.get("first_name", customer_profile.first_name)
                customer_profile.last_name = customer_meta.get("last_name", customer_profile.last_name)

        return user

    # 1. THREE ADMIN ACCOUNTS (Superadmin access with store_admin role)
    await upsert_user(
        email="admin@uwearnova.com",
        password="AdminPassword123!",
        user_type="admin",
        role_name="store_admin",
        staff_meta={
            "employee_code": "EMP-UWN-001",
            "department": "executive",
            "job_title": "Principal Store Administrator",
        },
    )
    await upsert_user(
        email="admin2@uwearnova.com",
        password="AdminPassword123!",
        user_type="admin",
        role_name="store_admin",
        staff_meta={
            "employee_code": "EMP-UWN-002",
            "department": "operations",
            "job_title": "Operations & Retail Director",
        },
    )
    await upsert_user(
        email="admin3@uwearnova.com",
        password="AdminPassword123!",
        user_type="admin",
        role_name="store_admin",
        staff_meta={
            "employee_code": "EMP-UWN-003",
            "department": "technology",
            "job_title": "Systems & Inventory Administrator",
        },
    )

    # 2. STAFF ACCOUNTS
    await upsert_user(
        email="staff@uwearnova.com",
        password="StaffPassword123!",
        user_type="staff",
        role_name="order_manager",
        staff_meta={
            "employee_code": "EMP-UWN-010",
            "department": "operations",
            "job_title": "Senior Order Operations Manager",
        },
    )
    await upsert_user(
        email="inventory@uwearnova.com",
        password="StaffPassword123!",
        user_type="staff",
        role_name="inventory_manager",
        staff_meta={
            "employee_code": "EMP-UWN-020",
            "department": "warehouse",
            "job_title": "Head of Warehouse & Inventory",
        },
    )
    await upsert_user(
        email="support@uwearnova.com",
        password="StaffPassword123!",
        user_type="staff",
        role_name="customer_support",
        staff_meta={
            "employee_code": "EMP-UWN-030",
            "department": "support",
            "job_title": "Senior Client Support Specialist",
        },
    )

    # 3. CUSTOMER ACCOUNTS
    await upsert_user(
        email="customer@uwearnova.com",
        password="CustomerPassword123!",
        user_type="customer",
        role_name="customer",
        customer_meta={
            "first_name": "Ahmed",
            "last_name": "Khan",
            "phone": "+923001234567",
        },
    )
    await upsert_user(
        email="client@uwearnova.com",
        password="CustomerPassword123!",
        user_type="customer",
        role_name="customer",
        customer_meta={
            "first_name": "Zara",
            "last_name": "Malik",
            "phone": "+923219876543",
        },
    )

    # 3. Purge any leftover legacy @uninova accounts
    await purge_legacy_uninova_accounts(db)

    await db.flush()


async def run_seed(wipe_products: bool = True) -> None:
    """Standalone entrypoint to seed system roles, default users, locations, and clean catalog."""
    from app.core.database import AsyncSessionLocal
    from app.modules.rbac.service import seed_system_roles_and_permissions

    async with AsyncSessionLocal() as session:
        if wipe_products:
            print("Wiping all dummy products, variants, images, inventory, and sales...")
            await wipe_all_products(session)
        print("Seeding system roles and permissions...")
        await seed_system_roles_and_permissions(session)
        print("Seeding default inventory locations...")
        await seed_default_locations(session)
        print("Seeding admin, staff, and customer accounts...")
        await seed_default_users(session)
        print("Seeding categories and collections (products excluded)...")
        await seed_catalog_products(session, include_products=False)
        await session.commit()
        print("SUCCESS: Database cleanly re-seeded with 3 Admins, staff, customers, and clean catalog.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_seed(wipe_products=True))
