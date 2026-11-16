-- ==============================================================================
-- UniNova E-Commerce: Authentication Bridge, RBAC Helpers & Row Level Security
-- Migration: 20261116000002_auth_and_rbac.sql
-- Description: Bridges auth.users, creates permission helpers, enables RLS on 100%
--              of domain tables and defines granular policies.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Helper Functions for Auth & Permission Verification
-- ------------------------------------------------------------------------------

-- Helper to retrieve domain user ID from authenticated JWT auth.uid()
CREATE OR REPLACE FUNCTION auth.current_domain_user_id()
RETURNS BIGINT AS $$
  SELECT id FROM public.users WHERE auth_user_id = auth.uid() LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- Helper to check if caller has a specific operational permission
CREATE OR REPLACE FUNCTION auth.has_permission(p_code TEXT)
RETURNS BOOLEAN AS $$
DECLARE
  v_user_type TEXT;
  v_has_perm BOOLEAN;
BEGIN
  -- Check if user is platform admin
  SELECT user_type INTO v_user_type
  FROM public.users
  WHERE auth_user_id = auth.uid();

  IF v_user_type = 'admin' THEN
    RETURN true;
  END IF;

  -- Check through assigned roles
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles ur
    JOIN public.role_permissions rp ON ur.role_id = rp.role_id
    JOIN public.permissions p ON rp.permission_id = p.id
    JOIN public.users u ON ur.user_id = u.id
    WHERE u.auth_user_id = auth.uid()
      AND p.code = p_code
  ) INTO v_has_perm;

  RETURN COALESCE(v_has_perm, false);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- Helper to check if caller is any staff member
CREATE OR REPLACE FUNCTION auth.is_staff()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.users
    WHERE auth_user_id = auth.uid()
      AND user_type IN ('staff', 'admin')
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- ------------------------------------------------------------------------------
-- 2. Trigger: Link Supabase auth.users to public.users & customer_profiles
-- ------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger AS $$
DECLARE
  v_new_user_id BIGINT;
  v_role_id BIGINT;
  v_user_type TEXT;
BEGIN
  v_user_type := COALESCE(NEW.raw_user_meta_data->>'user_type', 'customer');

  -- Insert domain user record
  INSERT INTO public.users (
    auth_user_id,
    email,
    phone,
    status,
    user_type,
    email_verified_at
  ) VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'phone',
    'active',
    v_user_type,
    NEW.email_confirmed_at
  ) RETURNING id INTO v_new_user_id;

  -- Create customer profile if user is a customer
  IF v_user_type = 'customer' THEN
    INSERT INTO public.customer_profiles (
      user_id,
      first_name,
      last_name,
      phone
    ) VALUES (
      v_new_user_id,
      NEW.raw_user_meta_data->>'first_name',
      NEW.raw_user_meta_data->>'last_name',
      NEW.raw_user_meta_data->>'phone'
    );

    -- Assign customer role if exists
    SELECT id INTO v_role_id FROM public.roles WHERE name = 'customer';
    IF v_role_id IS NOT NULL THEN
      INSERT INTO public.user_roles (user_id, role_id) VALUES (v_new_user_id, v_role_id)
      ON CONFLICT DO NOTHING;
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- Hook into auth.users lifecycle
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();

-- ------------------------------------------------------------------------------
-- 3. Enable Row Level Security (RLS) on 100% of Domain Tables
-- ------------------------------------------------------------------------------

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.password_resets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.staff_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.support_ticket_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.staff_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.carts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cart_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wishlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wishlist_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shipping_zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shipping_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.checkout_idempotency ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.refunds ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shipment_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shipment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.return_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.return_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coupons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coupon_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.announcement_bars ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.homepage_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.offline_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.offline_sale_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- 4. RLS Policies: Catalog & Content (Public Read / Staff Write)
-- ------------------------------------------------------------------------------

-- Categories
CREATE POLICY "Public read active categories" ON public.categories
  FOR SELECT USING (is_active = true OR auth.is_staff());

CREATE POLICY "Staff manage categories" ON public.categories
  FOR ALL USING (auth.has_permission('categories.manage'));

-- Collections
CREATE POLICY "Public read active collections" ON public.collections
  FOR SELECT USING (is_active = true OR auth.is_staff());

CREATE POLICY "Staff manage collections" ON public.collections
  FOR ALL USING (auth.has_permission('collections.manage'));

-- Products
CREATE POLICY "Public read active products" ON public.products
  FOR SELECT USING (status = 'active' OR auth.is_staff());

CREATE POLICY "Staff manage products" ON public.products
  FOR ALL USING (auth.has_permission('products.update') OR auth.has_permission('products.create'));

-- Product Variants
CREATE POLICY "Public read active variants" ON public.product_variants
  FOR SELECT USING (is_active = true OR auth.is_staff());

CREATE POLICY "Staff manage variants" ON public.product_variants
  FOR ALL USING (auth.has_permission('products.update'));

-- Product Images
CREATE POLICY "Public read product images" ON public.product_images
  FOR SELECT USING (true);

CREATE POLICY "Staff manage product images" ON public.product_images
  FOR ALL USING (auth.has_permission('products.update'));

-- Product Collections
CREATE POLICY "Public read product collections" ON public.product_collections
  FOR SELECT USING (true);

CREATE POLICY "Staff manage product collections" ON public.product_collections
  FOR ALL USING (auth.has_permission('collections.manage'));

-- Announcement Bars, Campaigns, Content Pages
CREATE POLICY "Public read active announcement bars" ON public.announcement_bars
  FOR SELECT USING (is_active = true OR auth.is_staff());

CREATE POLICY "Staff manage announcement bars" ON public.announcement_bars
  FOR ALL USING (auth.has_permission('content.manage'));

CREATE POLICY "Public read active campaigns" ON public.homepage_campaigns
  FOR SELECT USING (is_active = true OR auth.is_staff());

CREATE POLICY "Staff manage campaigns" ON public.homepage_campaigns
  FOR ALL USING (auth.has_permission('content.manage'));

CREATE POLICY "Public read published content pages" ON public.content_pages
  FOR SELECT USING (is_published = true OR auth.is_staff());

CREATE POLICY "Staff manage content pages" ON public.content_pages
  FOR ALL USING (auth.has_permission('content.manage'));

-- Shipping Methods & Zones
CREATE POLICY "Public read shipping zones" ON public.shipping_zones
  FOR SELECT USING (is_active = true OR auth.is_staff());

CREATE POLICY "Staff manage shipping zones" ON public.shipping_zones
  FOR ALL USING (auth.has_permission('settings.manage'));

CREATE POLICY "Public read shipping methods" ON public.shipping_methods
  FOR SELECT USING (is_active = true OR auth.is_staff());

CREATE POLICY "Staff manage shipping methods" ON public.shipping_methods
  FOR ALL USING (auth.has_permission('settings.manage'));

-- ------------------------------------------------------------------------------
-- 5. RLS Policies: Customer Data, Addresses & Profiles
-- ------------------------------------------------------------------------------

-- Users
CREATE POLICY "Users read own record" ON public.users
  FOR SELECT USING (auth_user_id = auth.uid() OR auth.is_staff());

CREATE POLICY "Users update own record" ON public.users
  FOR UPDATE USING (auth_user_id = auth.uid());

-- Customer Profiles
CREATE POLICY "Customer read own profile" ON public.customer_profiles
  FOR SELECT USING (user_id = auth.current_domain_user_id() OR auth.has_permission('customers.read'));

CREATE POLICY "Customer update own profile" ON public.customer_profiles
  FOR UPDATE USING (user_id = auth.current_domain_user_id());

-- Addresses
CREATE POLICY "Customer manage own addresses" ON public.addresses
  FOR ALL USING (user_id = auth.current_domain_user_id() OR auth.has_permission('customers.read'));

-- ------------------------------------------------------------------------------
-- 6. RLS Policies: Cart & Wishlist
-- ------------------------------------------------------------------------------

-- Carts (authenticated customer owns by user_id; anonymous guest owns by matching token)
CREATE POLICY "Access own cart" ON public.carts
  FOR ALL USING (
    (user_id IS NOT NULL AND user_id = auth.current_domain_user_id())
    OR (anonymous_token IS NOT NULL)
  );

CREATE POLICY "Access own cart items" ON public.cart_items
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.carts c
      WHERE c.id = cart_items.cart_id
        AND ((c.user_id = auth.current_domain_user_id()) OR (c.anonymous_token IS NOT NULL))
    )
  );

-- Wishlist
CREATE POLICY "Customer manage own wishlist" ON public.wishlists
  FOR ALL USING (user_id = auth.current_domain_user_id());

CREATE POLICY "Customer manage own wishlist items" ON public.wishlist_items
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.wishlists w
      WHERE w.id = wishlist_items.wishlist_id
        AND w.user_id = auth.current_domain_user_id()
    )
  );

-- ------------------------------------------------------------------------------
-- 7. RLS Policies: Orders & Fulfillment
-- ------------------------------------------------------------------------------

-- Orders
CREATE POLICY "Customer view own orders" ON public.orders
  FOR SELECT USING (
    user_id = auth.current_domain_user_id()
    OR auth.has_permission('orders.read')
  );

CREATE POLICY "Staff manage orders" ON public.orders
  FOR ALL USING (auth.has_permission('orders.update'));

-- Order Items
CREATE POLICY "Customer view own order items" ON public.order_items
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.orders o
      WHERE o.id = order_items.order_id
        AND (o.user_id = auth.current_domain_user_id() OR auth.has_permission('orders.read'))
    )
  );

-- Order Status History
CREATE POLICY "View order status history" ON public.order_status_history
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.orders o
      WHERE o.id = order_status_history.order_id
        AND (o.user_id = auth.current_domain_user_id() OR auth.has_permission('orders.read'))
    )
  );

-- Shipments & Events
CREATE POLICY "Public read tracking by tracking number" ON public.shipments
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.orders o
      WHERE o.id = shipments.order_id
        AND (o.user_id = auth.current_domain_user_id() OR auth.has_permission('orders.read'))
    )
    OR auth.has_permission('shipments.manage')
  );

CREATE POLICY "Staff manage shipments" ON public.shipments
  FOR ALL USING (auth.has_permission('shipments.manage'));

CREATE POLICY "Public read shipment events" ON public.shipment_events
  FOR SELECT USING (true);

-- Returns
CREATE POLICY "Customer view own returns" ON public.return_requests
  FOR SELECT USING (
    user_id = auth.current_domain_user_id()
    OR auth.has_permission('returns.read')
  );

CREATE POLICY "Customer submit return request" ON public.return_requests
  FOR INSERT WITH CHECK (user_id = auth.current_domain_user_id());

CREATE POLICY "Staff manage returns" ON public.return_requests
  FOR ALL USING (auth.has_permission('returns.resolve'));

CREATE POLICY "Access return items" ON public.return_items
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.return_requests r
      WHERE r.id = return_items.return_request_id
        AND (r.user_id = auth.current_domain_user_id() OR auth.has_permission('returns.read'))
    )
  );

-- ------------------------------------------------------------------------------
-- 8. RLS Policies: Reviews & Ratings
-- ------------------------------------------------------------------------------

CREATE POLICY "Public read approved reviews" ON public.product_reviews
  FOR SELECT USING (is_approved = true OR auth.is_staff());

CREATE POLICY "Customer submit review" ON public.product_reviews
  FOR INSERT WITH CHECK (user_id = auth.current_domain_user_id());

CREATE POLICY "Customer update own review" ON public.product_reviews
  FOR UPDATE USING (user_id = auth.current_domain_user_id());

CREATE POLICY "Staff moderate reviews" ON public.product_reviews
  FOR ALL USING (auth.has_permission('reviews.moderate'));

-- ------------------------------------------------------------------------------
-- 9. RLS Policies: Inventory & Staff Operations (Staff-Only)
-- ------------------------------------------------------------------------------

CREATE POLICY "Staff view inventory" ON public.inventory_locations
  FOR ALL USING (auth.has_permission('inventory.read'));

CREATE POLICY "Staff view inventory items" ON public.inventory_items
  FOR ALL USING (auth.has_permission('inventory.read'));

CREATE POLICY "Staff view inventory movements" ON public.inventory_movements
  FOR ALL USING (auth.has_permission('inventory.read'));

CREATE POLICY "Staff manage offline sales" ON public.offline_sales
  FOR ALL USING (auth.has_permission('dashboard.read') OR auth.is_staff());

CREATE POLICY "Staff manage offline sale items" ON public.offline_sale_items
  FOR ALL USING (auth.has_permission('dashboard.read') OR auth.is_staff());

CREATE POLICY "Staff view tickets" ON public.support_tickets
  FOR ALL USING (
    user_id = auth.current_domain_user_id()
    OR auth.is_staff()
  );

CREATE POLICY "Staff view ticket messages" ON public.support_ticket_messages
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.support_tickets st
      WHERE st.id = support_ticket_messages.ticket_id
        AND (st.user_id = auth.current_domain_user_id() OR auth.is_staff())
    )
  );

CREATE POLICY "Staff view audit logs" ON public.audit_logs
  FOR SELECT USING (auth.has_permission('audit.read'));

CREATE POLICY "Admin manage roles and permissions" ON public.roles
  FOR ALL USING (auth.has_permission('roles.manage'));

CREATE POLICY "Staff read permissions" ON public.permissions
  FOR SELECT USING (auth.is_staff());

CREATE POLICY "Admin manage role permissions" ON public.role_permissions
  FOR ALL USING (auth.has_permission('roles.manage'));

CREATE POLICY "Admin manage user roles" ON public.user_roles
  FOR ALL USING (auth.has_permission('roles.manage'));
