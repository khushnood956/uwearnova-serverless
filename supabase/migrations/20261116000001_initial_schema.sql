-- ==============================================================================
-- UniNova E-Commerce: Initial Relational Database Schema
-- Migration: 20261116000001_initial_schema.sql
-- Description: Core 50 tables with PostgreSQL types, indexes, and constraints.
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Helper trigger function to maintain updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------------------------
-- 2. Identity & Access Management (Core Users & RBAC)
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  auth_user_id UUID UNIQUE, -- REFERENCES auth.users(id) ON DELETE CASCADE
  email VARCHAR(255) NOT NULL UNIQUE,
  phone VARCHAR(32),
  status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'pending_verification', 'suspended', 'disabled', 'locked')),
  user_type VARCHAR(32) NOT NULL DEFAULT 'customer' CHECK (user_type IN ('customer', 'staff', 'admin')),
  email_verified_at TIMESTAMPTZ,
  last_login_at TIMESTAMPTZ,
  failed_login_attempts INT NOT NULL DEFAULT 0,
  locked_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON public.users(status);
CREATE INDEX IF NOT EXISTS idx_users_auth_user_id ON public.users(auth_user_id);

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.customer_profiles (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
  first_name VARCHAR(64),
  last_name VARCHAR(64),
  phone VARCHAR(32),
  preferences JSONB NOT NULL DEFAULT '{"marketing_email": false, "marketing_sms": false, "marketing_whatsapp": false, "language": "en", "currency": "PKR"}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_customer_profiles_user_id ON public.customer_profiles(user_id);

CREATE TRIGGER update_customer_profiles_updated_at BEFORE UPDATE ON public.customer_profiles
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.addresses (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  label VARCHAR(64),
  full_name VARCHAR(128) NOT NULL,
  phone VARCHAR(32) NOT NULL,
  street_address TEXT NOT NULL,
  apartment_suite VARCHAR(128),
  city VARCHAR(128) NOT NULL,
  province VARCHAR(64),
  postal_code VARCHAR(32),
  country_code VARCHAR(2) NOT NULL DEFAULT 'PK',
  delivery_instructions TEXT,
  is_default BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_addresses_user_default ON public.addresses(user_id, is_default);

CREATE TRIGGER update_addresses_updated_at BEFORE UPDATE ON public.addresses
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RBAC Tables
CREATE TABLE IF NOT EXISTS public.roles (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(64) NOT NULL UNIQUE,
  display_name VARCHAR(128) NOT NULL,
  description VARCHAR(255),
  is_system BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.permissions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code VARCHAR(64) NOT NULL UNIQUE,
  display_name VARCHAR(128),
  description VARCHAR(255),
  category VARCHAR(64) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_permissions_category ON public.permissions(category);

CREATE TABLE IF NOT EXISTS public.role_permissions (
  role_id BIGINT NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
  permission_id BIGINT NOT NULL REFERENCES public.permissions(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS public.user_roles (
  user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  role_id BIGINT NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

-- Legacy auth tables (retained for backward compatibility and archival)
CREATE TABLE IF NOT EXISTS public.refresh_tokens (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  revoked BOOLEAN NOT NULL DEFAULT false,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.password_resets (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  used BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- 3. Staff & Operations Work Queues
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.staff_profiles (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
  employee_id VARCHAR(32) NOT NULL UNIQUE,
  department VARCHAR(64) NOT NULL,
  assigned_role VARCHAR(64),
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.support_tickets (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ticket_number VARCHAR(64) NOT NULL UNIQUE,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  order_id BIGINT, -- added as foreign key after orders table creation
  subject VARCHAR(255) NOT NULL,
  priority VARCHAR(32) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  status VARCHAR(32) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
  assigned_staff_id BIGINT REFERENCES public.staff_profiles(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON public.support_tickets(status);

CREATE TABLE IF NOT EXISTS public.support_ticket_messages (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ticket_id BIGINT NOT NULL REFERENCES public.support_tickets(id) ON DELETE CASCADE,
  sender_user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  message TEXT NOT NULL,
  is_internal BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket ON public.support_ticket_messages(ticket_id);

CREATE TABLE IF NOT EXISTS public.staff_tasks (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  staff_id BIGINT NOT NULL REFERENCES public.staff_profiles(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
  due_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- 4. Catalog, Products & Inventory
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.categories (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  slug VARCHAR(128) NOT NULL UNIQUE,
  description TEXT,
  image_url TEXT,
  parent_id BIGINT REFERENCES public.categories(id) ON DELETE SET NULL,
  sort_order INT NOT NULL DEFAULT 0,
  level INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT true,
  is_coming_soon BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_categories_slug ON public.categories(slug);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON public.categories(parent_id, is_active);

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON public.categories
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.collections (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  slug VARCHAR(128) NOT NULL UNIQUE,
  description TEXT,
  image_url TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_collections_slug ON public.collections(slug);

CREATE TRIGGER update_collections_updated_at BEFORE UPDATE ON public.collections
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.products (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  category_id BIGINT NOT NULL REFERENCES public.categories(id) ON DELETE RESTRICT,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL UNIQUE,
  subtitle VARCHAR(255),
  description TEXT,
  brand_label VARCHAR(64) NOT NULL DEFAULT 'UniNova',
  status VARCHAR(32) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
  price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
  original_price NUMERIC(12, 2) CHECK (original_price IS NULL OR original_price >= 0),
  is_featured BOOLEAN NOT NULL DEFAULT false,
  is_trending BOOLEAN NOT NULL DEFAULT false,
  is_new_arrival BOOLEAN NOT NULL DEFAULT false,
  fabric_care JSONB,
  delivery_notes TEXT,
  rating NUMERIC(3, 2) NOT NULL DEFAULT 0.00,
  review_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_products_slug ON public.products(slug);
CREATE INDEX IF NOT EXISTS idx_products_category ON public.products(category_id, status);
CREATE INDEX IF NOT EXISTS idx_products_featured ON public.products(status, is_featured);

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON public.products
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.product_variants (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  sku VARCHAR(64) NOT NULL UNIQUE,
  size VARCHAR(32) NOT NULL,
  color_name VARCHAR(64) NOT NULL,
  color_hex VARCHAR(16),
  price NUMERIC(12, 2) CHECK (price IS NULL OR price >= 0),
  inventory_count INT NOT NULL DEFAULT 0 CHECK (inventory_count >= 0),
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_product_variants_size_color UNIQUE (product_id, size, color_name)
);
CREATE INDEX IF NOT EXISTS idx_variants_product ON public.product_variants(product_id, is_active);
CREATE INDEX IF NOT EXISTS idx_variants_sku ON public.product_variants(sku);

CREATE TRIGGER update_product_variants_updated_at BEFORE UPDATE ON public.product_variants
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.product_images (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  image_url TEXT NOT NULL,
  alt_text VARCHAR(255),
  sort_order INT NOT NULL DEFAULT 0,
  is_primary BOOLEAN NOT NULL DEFAULT false,
  width INT,
  height INT,
  file_size INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_product_images_product ON public.product_images(product_id, is_primary);

CREATE TABLE IF NOT EXISTS public.product_collections (
  product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  collection_id BIGINT NOT NULL REFERENCES public.collections(id) ON DELETE CASCADE,
  PRIMARY KEY (product_id, collection_id)
);

-- Inventory Management
CREATE TABLE IF NOT EXISTS public.inventory_locations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  code VARCHAR(64) NOT NULL UNIQUE,
  address_line_1 VARCHAR(255),
  city VARCHAR(128),
  postal_code VARCHAR(32),
  country_code VARCHAR(2) NOT NULL DEFAULT 'PK',
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.inventory_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  variant_id BIGINT NOT NULL REFERENCES public.product_variants(id) ON DELETE CASCADE,
  location_id BIGINT NOT NULL REFERENCES public.inventory_locations(id) ON DELETE CASCADE,
  quantity_on_hand INT NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
  quantity_reserved INT NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
  reorder_threshold INT NOT NULL DEFAULT 5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_inventory_items_variant_location UNIQUE (variant_id, location_id)
);

CREATE TABLE IF NOT EXISTS public.inventory_movements (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  inventory_item_id BIGINT NOT NULL REFERENCES public.inventory_items(id) ON DELETE CASCADE,
  movement_type VARCHAR(32) NOT NULL CHECK (movement_type IN ('initial_stock', 'purchase_receipt', 'sale_deduction', 'return_restock', 'manual_adjustment', 'damaged_writeoff')),
  quantity INT NOT NULL,
  reference_type VARCHAR(64),
  reference_id VARCHAR(64),
  notes TEXT,
  created_by_user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_movements_item ON public.inventory_movements(inventory_item_id);

-- ------------------------------------------------------------------------------
-- 5. Cart & Wishlist
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.carts (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
  anonymous_token VARCHAR(64) UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_carts_user ON public.carts(user_id);
CREATE INDEX IF NOT EXISTS idx_carts_anon ON public.carts(anonymous_token);

CREATE TABLE IF NOT EXISTS public.cart_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cart_id BIGINT NOT NULL REFERENCES public.carts(id) ON DELETE CASCADE,
  variant_id BIGINT NOT NULL REFERENCES public.product_variants(id) ON DELETE CASCADE,
  quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_cart_items_cart_variant UNIQUE (cart_id, variant_id)
);

CREATE TABLE IF NOT EXISTS public.wishlists (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.wishlist_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  wishlist_id BIGINT NOT NULL REFERENCES public.wishlists(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_wishlist_items_product UNIQUE (wishlist_id, product_id)
);

-- ------------------------------------------------------------------------------
-- 6. Shipping & Delivery
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.shipping_zones (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  country_code VARCHAR(2) NOT NULL DEFAULT 'PK',
  regions JSONB NOT NULL DEFAULT '[]'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.shipping_methods (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  zone_id BIGINT REFERENCES public.shipping_zones(id) ON DELETE CASCADE,
  name VARCHAR(128) NOT NULL,
  code VARCHAR(64) NOT NULL UNIQUE,
  base_rate NUMERIC(12, 2) NOT NULL DEFAULT 350.00,
  free_threshold NUMERIC(12, 2) NOT NULL DEFAULT 5000.00,
  estimated_days VARCHAR(32) NOT NULL DEFAULT '2-4 business days',
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- 7. Orders & Checkout
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.orders (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_number VARCHAR(64) NOT NULL UNIQUE,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  customer_email VARCHAR(255) NOT NULL,
  customer_phone VARCHAR(32) NOT NULL,
  customer_name VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending_confirmation' CHECK (status IN ('pending_confirmation', 'confirmed', 'processing', 'packed', 'shipped', 'delivered', 'cancelled', 'return_requested', 'returned', 'refunded')),
  payment_status VARCHAR(32) NOT NULL DEFAULT 'unpaid' CHECK (payment_status IN ('unpaid', 'authorized', 'paid', 'refunded', 'failed')),
  fulfillment_status VARCHAR(32) NOT NULL DEFAULT 'unfulfilled' CHECK (fulfillment_status IN ('unfulfilled', 'partially_fulfilled', 'fulfilled', 'cancelled')),
  payment_method VARCHAR(32) NOT NULL DEFAULT 'cod',
  currency_code VARCHAR(3) NOT NULL DEFAULT 'PKR',
  subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  shipping_fee NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  grand_total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  shipping_method_code VARCHAR(64) NOT NULL DEFAULT 'standard',
  shipping_method_name VARCHAR(128) NOT NULL DEFAULT 'Standard Delivery',
  shipping_address JSONB NOT NULL,
  customer_note TEXT,
  placed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON public.orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_user ON public.orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status, payment_status);

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON public.orders
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add deferred foreign key to support_tickets
ALTER TABLE public.support_tickets 
DROP CONSTRAINT IF EXISTS fk_support_tickets_order,
ADD CONSTRAINT fk_support_tickets_order FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS public.order_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
  variant_id BIGINT REFERENCES public.product_variants(id) ON DELETE SET NULL,
  product_name VARCHAR(255) NOT NULL,
  product_slug VARCHAR(255),
  sku VARCHAR(64) NOT NULL,
  size VARCHAR(32) NOT NULL,
  color VARCHAR(64) NOT NULL,
  unit_price NUMERIC(12, 2) NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  line_discount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  line_total NUMERIC(12, 2) NOT NULL,
  image_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON public.order_items(order_id);

CREATE TABLE IF NOT EXISTS public.order_status_history (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
  from_status VARCHAR(32) NOT NULL,
  to_status VARCHAR(32) NOT NULL,
  notes TEXT,
  created_by_user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_order_status_history_order ON public.order_status_history(order_id);

CREATE TABLE IF NOT EXISTS public.checkout_idempotency (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  idempotency_key VARCHAR(128) NOT NULL UNIQUE,
  order_id BIGINT REFERENCES public.orders(id) ON DELETE CASCADE,
  request_hash VARCHAR(64) NOT NULL,
  response_payload JSONB,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_idempotency_key ON public.checkout_idempotency(idempotency_key);

-- ------------------------------------------------------------------------------
-- 8. Payments & Refunds
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.payments (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
  provider_code VARCHAR(32) NOT NULL DEFAULT 'cod',
  payment_method VARCHAR(32) NOT NULL DEFAULT 'cod',
  status VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'authorized', 'captured', 'paid', 'failed', 'refunded')),
  amount NUMERIC(12, 2) NOT NULL,
  currency_code VARCHAR(3) NOT NULL DEFAULT 'PKR',
  provider_reference VARCHAR(128),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_payments_order ON public.payments(order_id);

CREATE TABLE IF NOT EXISTS public.payment_transactions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  payment_id BIGINT NOT NULL REFERENCES public.payments(id) ON DELETE CASCADE,
  transaction_type VARCHAR(32) NOT NULL CHECK (transaction_type IN ('authorization', 'capture', 'refund', 'void', 'cash_collection')),
  amount NUMERIC(12, 2) NOT NULL,
  currency_code VARCHAR(3) NOT NULL DEFAULT 'PKR',
  status VARCHAR(32) NOT NULL,
  gateway_response JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.payment_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  payment_id BIGINT REFERENCES public.payments(id) ON DELETE CASCADE,
  provider_code VARCHAR(32) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  provider_event_id VARCHAR(128),
  signature_verified BOOLEAN NOT NULL DEFAULT false,
  raw_payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.refunds (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  payment_id BIGINT NOT NULL REFERENCES public.payments(id) ON DELETE CASCADE,
  refund_number VARCHAR(64) NOT NULL UNIQUE,
  amount NUMERIC(12, 2) NOT NULL,
  currency_code VARCHAR(3) NOT NULL DEFAULT 'PKR',
  status VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
  reason TEXT,
  processed_by_user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- 9. Fulfillment & Courier Shipments
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.shipments (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
  tracking_number VARCHAR(128) NOT NULL UNIQUE,
  courier_name VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'manifested' CHECK (status IN ('manifested', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered', 'returned', 'failed_attempt')),
  shipped_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_shipments_tracking ON public.shipments(tracking_number);

CREATE TABLE IF NOT EXISTS public.shipment_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  shipment_id BIGINT NOT NULL REFERENCES public.shipments(id) ON DELETE CASCADE,
  order_item_id BIGINT NOT NULL REFERENCES public.order_items(id) ON DELETE CASCADE,
  quantity INT NOT NULL CHECK (quantity > 0)
);

CREATE TABLE IF NOT EXISTS public.shipment_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  shipment_id BIGINT NOT NULL REFERENCES public.shipments(id) ON DELETE CASCADE,
  status VARCHAR(32) NOT NULL,
  location VARCHAR(128),
  description TEXT,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- 10. Returns, Exchanges & Reviews
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.return_requests (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  return_number VARCHAR(64) NOT NULL UNIQUE,
  order_id BIGINT NOT NULL REFERENCES public.orders(id) ON DELETE RESTRICT,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  request_type VARCHAR(32) NOT NULL DEFAULT 'return' CHECK (request_type IN ('return', 'exchange')),
  status VARCHAR(32) NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted', 'approved', 'rejected', 'item_received', 'completed')),
  refund_status VARCHAR(32),
  refund_amount NUMERIC(12, 2),
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_returns_user ON public.return_requests(user_id);

CREATE TABLE IF NOT EXISTS public.return_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  return_request_id BIGINT NOT NULL REFERENCES public.return_requests(id) ON DELETE CASCADE,
  order_item_id BIGINT NOT NULL REFERENCES public.order_items(id) ON DELETE RESTRICT,
  quantity INT NOT NULL CHECK (quantity > 0),
  reason VARCHAR(64) NOT NULL,
  condition VARCHAR(32),
  status VARCHAR(32) NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS public.product_reviews (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  title VARCHAR(128),
  comment TEXT,
  is_approved BOOLEAN NOT NULL DEFAULT false,
  verified_purchase BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reviews_product_approved ON public.product_reviews(product_id, is_approved);

-- ------------------------------------------------------------------------------
-- 11. Promotions & Content CMS
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.coupons (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code VARCHAR(64) NOT NULL UNIQUE,
  discount_type VARCHAR(32) NOT NULL CHECK (discount_type IN ('percentage', 'fixed_amount')),
  discount_value NUMERIC(12, 2) NOT NULL CHECK (discount_value > 0),
  minimum_order_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  usage_limit INT,
  usage_count INT NOT NULL DEFAULT 0,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_until TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coupons_code ON public.coupons(code, is_active);

CREATE TABLE IF NOT EXISTS public.coupon_redemptions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  coupon_id BIGINT NOT NULL REFERENCES public.coupons(id) ON DELETE RESTRICT,
  order_id BIGINT NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
  user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  discount_amount NUMERIC(12, 2) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.announcement_bars (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  text VARCHAR(255) NOT NULL,
  link_url TEXT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  display_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.homepage_campaigns (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title VARCHAR(128) NOT NULL,
  subtitle VARCHAR(255),
  cta_text VARCHAR(64),
  cta_url TEXT,
  image_url TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.content_pages (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug VARCHAR(128) NOT NULL UNIQUE,
  title VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  meta_title VARCHAR(255),
  meta_description TEXT,
  is_published BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_content_pages_slug ON public.content_pages(slug);

-- ------------------------------------------------------------------------------
-- 12. Offline Sales (POS Walk-in Transactions) & Compliance Audit
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.offline_sales (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  receipt_number VARCHAR(64) NOT NULL UNIQUE,
  staff_id BIGINT REFERENCES public.staff_profiles(id) ON DELETE RESTRICT,
  customer_name VARCHAR(128),
  customer_phone VARCHAR(32),
  customer_email VARCHAR(255),
  payment_method VARCHAR(32) NOT NULL DEFAULT 'cash' CHECK (payment_method IN ('cash', 'card', 'bank_transfer', 'split')),
  total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
  status VARCHAR(32) NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'voided', 'refunded')),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_offline_sales_receipt ON public.offline_sales(receipt_number);

CREATE TABLE IF NOT EXISTS public.offline_sale_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sale_id BIGINT NOT NULL REFERENCES public.offline_sales(id) ON DELETE CASCADE,
  variant_id BIGINT NOT NULL REFERENCES public.product_variants(id) ON DELETE RESTRICT,
  unit_price NUMERIC(12, 2) NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  line_total NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.audit_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
  actor_email VARCHAR(255),
  action VARCHAR(64) NOT NULL,
  entity_type VARCHAR(64) NOT NULL,
  entity_id VARCHAR(64),
  changes JSONB,
  ip_address VARCHAR(45),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON public.audit_logs(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON public.audit_logs(entity_type, entity_id);
