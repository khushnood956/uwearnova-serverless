-- ==============================================================================
-- UniNova E-Commerce: Staging & Development Seed Data
-- File: supabase/seed.sql
-- Description: Standard roles, permissions, warehouse, shipping methods,
--              categories, collections, and sample storefront products.
-- ==============================================================================

-- 1. Standard Permissions
INSERT INTO public.permissions (code, display_name, description, category) VALUES
  ('dashboard.read', 'View Dashboard', 'View operational dashboard metrics and summaries', 'dashboard'),
  ('products.read', 'View Products', 'View product catalog, variants, and stock levels', 'catalog'),
  ('products.create', 'Create Products', 'Create new product drafts and variants', 'catalog'),
  ('products.update', 'Update Products', 'Edit product details, pricing, and descriptions', 'catalog'),
  ('products.archive', 'Archive Products', 'Archive or unpublish products', 'catalog'),
  ('products.publish', 'Publish Products', 'Publish drafts to live customer storefront', 'catalog'),
  ('categories.manage', 'Manage Categories', 'Create, edit, and organize product categories', 'catalog'),
  ('collections.manage', 'Manage Collections', 'Curate and organize seasonal collections', 'catalog'),
  ('inventory.read', 'View Inventory', 'Inspect stock counts across variants and locations', 'inventory'),
  ('inventory.adjust', 'Adjust Inventory', 'Execute manual stock adjustments with audit reasons', 'inventory'),
  ('orders.read', 'View Orders', 'Search, view, and inspect customer orders', 'orders'),
  ('orders.update', 'Update Orders', 'Update order workflow and fulfillment states', 'orders'),
  ('orders.cancel', 'Cancel Orders', 'Cancel unfulfilled orders within policy', 'orders'),
  ('shipments.manage', 'Manage Shipments', 'Assign couriers, generate consignments, and update tracking', 'fulfillment'),
  ('customers.read', 'View Customers', 'View customer profiles and order histories', 'customers'),
  ('customers.update_status', 'Update Customer Status', 'Disable or modify customer account status', 'customers'),
  ('returns.read', 'View Returns', 'View doorstep exchange and return requests', 'returns'),
  ('returns.review', 'Review Returns', 'Inspect returned garments and assess condition', 'returns'),
  ('returns.resolve', 'Resolve Returns', 'Approve or reject exchanges and trigger replacement dispatch', 'returns'),
  ('payments.read', 'View Payments', 'View payment statuses and transaction logs', 'payments'),
  ('payments.reconcile', 'Reconcile Payments', 'Mark COD deliveries collected and reconcile courier settlements', 'payments'),
  ('refunds.create', 'Create Refunds', 'Approve and execute payment refunds', 'payments'),
  ('promotions.manage', 'Manage Promotions', 'Configure discount coupons and promotional campaigns', 'marketing'),
  ('reviews.moderate', 'Moderate Reviews', 'Approve or hide customer product reviews', 'marketing'),
  ('content.manage', 'Manage Content', 'Manage homepage banners and editorial content', 'marketing'),
  ('staff.read', 'View Staff Directory', 'View staff directory and operational assignments', 'staff'),
  ('staff.manage', 'Manage Staff Accounts', 'Create and modify staff accounts', 'staff'),
  ('roles.read', 'View Roles', 'Inspect available system roles and assigned permissions', 'rbac'),
  ('roles.manage', 'Manage Roles', 'Assign and modify staff roles', 'rbac'),
  ('reports.read', 'View Reports', 'Access sales, inventory, and performance reports', 'reports'),
  ('reports.export', 'Export Reports', 'Export sensitive analytical and operational data', 'reports'),
  ('settings.manage', 'Manage Settings', 'Modify store configurations, shipping rules, and policies', 'system'),
  ('audit.read', 'View Audit Trail', 'Inspect the full administrative audit trail', 'system')
ON CONFLICT (code) DO NOTHING;

-- 2. System Roles
INSERT INTO public.roles (name, display_name, description, is_system) VALUES
  ('store_admin', 'Store Administrator', 'Full access to all administrative, catalog, financial, and security capabilities.', true),
  ('catalog_manager', 'Catalog Manager', 'Manages products, categories, collections, and media assets.', true),
  ('order_manager', 'Order Operations Manager', 'Manages order processing, customer confirmations, and cancellations.', true),
  ('fulfillment_staff', 'Fulfillment & Dispatch Specialist', 'Picks, packs, and dispatches parcels and manages courier shipments.', true),
  ('inventory_manager', 'Inventory Controller', 'Oversees stock receipts, warehouse adjustments, and transfers.', true),
  ('support_staff', 'Customer Support Representative', 'Handles customer tickets, returns, and account inquiries.', true),
  ('customer', 'Storefront Customer', 'Standard retail shopper account with self-service orders and wishlist.', true)
ON CONFLICT (name) DO NOTHING;

-- Map All Permissions to store_admin
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r, public.permissions p
WHERE r.name = 'store_admin'
ON CONFLICT DO NOTHING;

-- Map Order Manager Permissions
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r
JOIN public.permissions p ON p.code IN ('dashboard.read', 'orders.read', 'orders.update', 'orders.cancel', 'customers.read', 'returns.read', 'payments.read')
WHERE r.name = 'order_manager'
ON CONFLICT DO NOTHING;

-- Map Catalog Manager Permissions
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r
JOIN public.permissions p ON p.code IN ('dashboard.read', 'products.read', 'products.create', 'products.update', 'products.archive', 'products.publish', 'categories.manage', 'collections.manage', 'inventory.read')
WHERE r.name = 'catalog_manager'
ON CONFLICT DO NOTHING;

-- 3. Warehouse Location
INSERT INTO public.inventory_locations (name, code, address_line_1, city, postal_code, country_code, is_active) VALUES
  ('Primary Fulfillment Center', 'WH-KHI-01', 'Korangi Industrial Area', 'Karachi', '74900', 'PK', true)
ON CONFLICT (code) DO NOTHING;

-- 4. Shipping Zones & Methods
INSERT INTO public.shipping_zones (name, country_code, regions, is_active) VALUES
  ('Pakistan Domestic', 'PK', '["Sindh", "Punjab", "KPK", "Balochistan", "Islamabad"]'::jsonb, true)
ON CONFLICT DO NOTHING;

INSERT INTO public.shipping_methods (zone_id, name, code, base_rate, free_threshold, estimated_days, is_active) VALUES
  (1, 'Standard Delivery', 'standard', 350.00, 5000.00, '2-4 business days', true),
  (1, 'Express Courier Delivery', 'express', 650.00, 10000.00, '1-2 business days', true)
ON CONFLICT (code) DO NOTHING;

-- 5. Categories (Root & Subdepartments)
INSERT INTO public.categories (name, slug, description, image_url, sort_order, is_coming_soon, is_active) VALUES
  ('Men', 'men', 'Structured blazers, refined linen shirts, tailored trousers, and elevated knitwear.', 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?q=80&w=1000&auto=format&fit=crop', 1, false, true),
  ('Women', 'women', 'Fluid silhouettes, tailored separates, sculptural dresses, and fine cashmere knits.', 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=1000&auto=format&fit=crop', 2, false, true),
  ('Kids', 'kids', 'Comfortable, premium cotton staples and warm fleece knitwear for children.', 'https://images.unsplash.com/photo-1503944583220-79d8926ad5e2?q=80&w=1000&auto=format&fit=crop', 3, false, true),
  ('Footwear', 'footwear', 'Handcrafted calfskin loafers, minimalist derbies, and modern sneakers.', 'https://images.unsplash.com/photo-1549298916-b41d501d3772?q=80&w=1000&auto=format&fit=crop', 4, true, true),
  ('Accessories', 'accessories', 'Architectural leather totes, minimal belts, and signature silk scarves.', 'https://images.unsplash.com/photo-1523293182086-7651a899d37f?q=80&w=1000&auto=format&fit=crop', 5, true, true),
  ('Perfumes', 'perfumes', 'Niche extrait de parfum, botanical accords, and subtle luxury fragrances.', 'https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?q=80&w=1000&auto=format&fit=crop', 6, true, true)
ON CONFLICT (slug) DO NOTHING;

-- Subcategories under Men, Women & Kids
INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Men''s Hoodies', 'men-hoodies', id, 1, true FROM public.categories WHERE slug = 'men'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Men''s Jackets', 'men-jackets', id, 2, true FROM public.categories WHERE slug = 'men'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Men''s T-Shirts', 'men-t-shirts', id, 3, true FROM public.categories WHERE slug = 'men'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Men''s Sweaters', 'men-sweaters', id, 4, true FROM public.categories WHERE slug = 'men'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Men''s Jeans & Pants', 'men-jeans-pants', id, 5, true FROM public.categories WHERE slug = 'men'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Women''s Hoodies', 'women-hoodies', id, 1, true FROM public.categories WHERE slug = 'women'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Women''s Jackets', 'women-jackets', id, 2, true FROM public.categories WHERE slug = 'women'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Women''s T-Shirts', 'women-t-shirts', id, 3, true FROM public.categories WHERE slug = 'women'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.categories (name, slug, parent_id, sort_order, is_active)
SELECT 'Women''s Sweaters', 'women-sweaters', id, 4, true FROM public.categories WHERE slug = 'women'
ON CONFLICT (slug) DO NOTHING;

-- 6. Curated Collections
INSERT INTO public.collections (name, slug, description, sort_order, is_active) VALUES
  ('New Arrivals', 'new-arrivals', 'The latest contemporary additions to the UniNova atelier.', 1, true),
  ('Signature Essentials', 'essentials', 'Timeless staples crafted from premium natural fibres.', 2, true),
  ('The Summer Linen Edit', 'summer-linen', 'Breathable Irish and Egyptian linen for effortless summer elegance.', 3, true)
ON CONFLICT (slug) DO NOTHING;

-- 7. Sample Products
INSERT INTO public.products (
  category_id, name, slug, subtitle, description, brand_label, status,
  price, original_price, is_featured, is_trending, is_new_arrival, rating, review_count
) VALUES
  (
    (SELECT id FROM public.categories WHERE slug = 'men-jackets' LIMIT 1),
    'Relaxed Linen Overshirt',
    'relaxed-linen-overshirt',
    'Pure washed French linen in sand stone',
    'Cut for an easy, relaxed drape, this overshirt is crafted from breathable European linen. Finished with horn buttons and double chest patch pockets.',
    'UniNova Atelier',
    'active',
    8950.00,
    11500.00,
    true,
    true,
    true,
    4.9,
    14
  ),
  (
    (SELECT id FROM public.categories WHERE slug = 'men-jeans-pants' LIMIT 1),
    'Pleated Relaxed Trouser',
    'pleated-relaxed-trouser',
    'Italian cotton-twill with double forward pleats',
    'A contemporary wide-leg silhouette featuring double pleats, side adjusters, and an unfinished hem ready for bespoke tailoring.',
    'UniNova Sartorial',
    'active',
    12500.00,
    14500.00,
    true,
    false,
    true,
    4.8,
    9
  ),
  (
    (SELECT id FROM public.categories WHERE slug = 'women' LIMIT 1),
    'Sculptural Drape Midi Dress',
    'sculptural-drape-midi-dress',
    'Heavyweight mulberry silk in ivory',
    'Fluid and architectural, this midi dress features an asymmetric cowl neckline and gentle waist gathering for evening events.',
    'UniNova Atelier',
    'active',
    18500.00,
    NULL,
    true,
    true,
    true,
    5.0,
    8
  )
ON CONFLICT (slug) DO NOTHING;

-- Sample Product Variants
INSERT INTO public.product_variants (product_id, sku, size, color_name, color_hex, price, inventory_count, is_active)
SELECT p.id, 'SHIRT-LINEN-SAND-M', 'M', 'Sand Stone', '#D2B48C', 8950.00, 25, true
FROM public.products p WHERE p.slug = 'relaxed-linen-overshirt'
ON CONFLICT (sku) DO NOTHING;

INSERT INTO public.product_variants (product_id, sku, size, color_name, color_hex, price, inventory_count, is_active)
SELECT p.id, 'SHIRT-LINEN-SAND-L', 'L', 'Sand Stone', '#D2B48C', 8950.00, 30, true
FROM public.products p WHERE p.slug = 'relaxed-linen-overshirt'
ON CONFLICT (sku) DO NOTHING;

INSERT INTO public.product_variants (product_id, sku, size, color_name, color_hex, price, inventory_count, is_active)
SELECT p.id, 'TROUSER-TWILL-NAVY-32', '32', 'Midnight Navy', '#000080', 12500.00, 15, true
FROM public.products p WHERE p.slug = 'pleated-relaxed-trouser'
ON CONFLICT (sku) DO NOTHING;

INSERT INTO public.product_variants (product_id, sku, size, color_name, color_hex, price, inventory_count, is_active)
SELECT p.id, 'DRESS-SILK-IVORY-S', 'S', 'Ivory', '#FFFFF0', 18500.00, 12, true
FROM public.products p WHERE p.slug = 'sculptural-drape-midi-dress'
ON CONFLICT (sku) DO NOTHING;

-- Sample Product Images
INSERT INTO public.product_images (product_id, image_url, alt_text, sort_order, is_primary)
SELECT p.id, 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?q=80&w=1000&auto=format&fit=crop', 'Relaxed Linen Overshirt Front View', 1, true
FROM public.products p WHERE p.slug = 'relaxed-linen-overshirt'
ON CONFLICT DO NOTHING;

INSERT INTO public.product_images (product_id, image_url, alt_text, sort_order, is_primary)
SELECT p.id, 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=1000&auto=format&fit=crop', 'Sculptural Drape Midi Dress Front View', 1, true
FROM public.products p WHERE p.slug = 'sculptural-drape-midi-dress'
ON CONFLICT DO NOTHING;

-- 8. Content Announcement & Campaign
INSERT INTO public.announcement_bars (text, link_url, is_active, display_order) VALUES
  ('Complimentary express delivery nationwide on all orders exceeding PKR 5,000.', '/shipping-delivery', true, 1)
ON CONFLICT DO NOTHING;

INSERT INTO public.homepage_campaigns (title, subtitle, cta_text, cta_url, is_active, sort_order) VALUES
  ('The Atelier Collection', 'Understated luxury tailored for the contemporary wardrobe.', 'Explore The Edit', '/collections/women', true, 1)
ON CONFLICT DO NOTHING;

-- 9. Welcome Coupon
INSERT INTO public.coupons (code, discount_type, discount_value, minimum_order_amount, is_active) VALUES
  ('WELCOME10', 'percentage', 10.00, 3000.00, true)
ON CONFLICT (code) DO NOTHING;
