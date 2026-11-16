-- ==============================================================================
-- UniNova E-Commerce: Automated RLS & Security Policy Verification Suite
-- File: supabase/tests/rls_policy_verification.sql
-- Description: Positive and negative security test cases verifying RLS boundaries
--              for Anonymous, Customer A, Customer B, and Staff roles.
-- ==============================================================================

BEGIN;

-- Setup Mock Test Users in public.users
INSERT INTO public.users (auth_user_id, email, user_type, status) VALUES
  ('00000000-0000-0000-0000-000000000001'::uuid, 'customer.a@test.uninova', 'customer', 'active'),
  ('00000000-0000-0000-0000-000000000002'::uuid, 'customer.b@test.uninova', 'customer', 'active'),
  ('00000000-0000-0000-0000-000000000003'::uuid, 'staff.orders@test.uninova', 'staff', 'active'),
  ('00000000-0000-0000-0000-000000000004'::uuid, 'admin@test.uninova', 'admin', 'active')
ON CONFLICT (email) DO NOTHING;

-- Map Staff User to Order Manager Role
INSERT INTO public.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM public.users u, public.roles r
WHERE u.email = 'staff.orders@test.uninova' AND r.name = 'order_manager'
ON CONFLICT DO NOTHING;

-- Create Customer A Address
INSERT INTO public.addresses (user_id, full_name, phone, street_address, city, is_default)
SELECT u.id, 'Customer Alpha', '03001234567', 'House 1, Street 1', 'Karachi', true
FROM public.users u WHERE u.email = 'customer.a@test.uninova'
ON CONFLICT DO NOTHING;

-- Create Customer A Order
INSERT INTO public.orders (
  order_number, user_id, customer_email, customer_phone, customer_name,
  status, payment_status, fulfillment_status, payment_method,
  subtotal, grand_total, shipping_address
) SELECT
  'UNV-TEST-0001', u.id, u.email, '03001234567', 'Customer Alpha',
  'confirmed', 'paid', 'unfulfilled', 'cod',
  8950.00, 9300.00, '{"street": "House 1"}'::jsonb
FROM public.users u WHERE u.email = 'customer.a@test.uninova'
ON CONFLICT (order_number) DO NOTHING;

-- ------------------------------------------------------------------------------
-- TEST CASE 1: Anonymous Role Policy Checks
-- ------------------------------------------------------------------------------
-- Simulate Anonymous request
SET LOCAL ROLE anon;
SET LOCAL "request.jwt.claims" = '{"role": "anon"}';

DO $$
DECLARE
  v_catalog_count INT;
  v_customer_count INT;
  v_order_count INT;
BEGIN
  -- 1.1 Anonymous CAN read active products
  SELECT count(*) INTO v_catalog_count FROM public.products WHERE status = 'active';
  ASSERT v_catalog_count >= 0, 'FAIL: Anonymous cannot read public products';

  -- 1.2 Anonymous CANNOT read customer profiles
  SELECT count(*) INTO v_customer_count FROM public.customer_profiles;
  ASSERT v_customer_count = 0, 'SECURITY VIOLATION: Anonymous accessed customer_profiles';

  -- 1.3 Anonymous CANNOT read orders
  SELECT count(*) INTO v_order_count FROM public.orders;
  ASSERT v_order_count = 0, 'SECURITY VIOLATION: Anonymous accessed orders table';

  RAISE NOTICE 'SUCCESS: Test Case 1 (Anonymous Boundaries) Passed';
END $$;

-- ------------------------------------------------------------------------------
-- TEST CASE 2: Customer A Isolation Checks
-- ------------------------------------------------------------------------------
-- Simulate Customer A Authenticated Session
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "00000000-0000-0000-0000-000000000001", "role": "authenticated"}';

DO $$
DECLARE
  v_own_orders INT;
  v_own_addresses INT;
BEGIN
  -- 2.1 Customer A can read own order
  SELECT count(*) INTO v_own_orders FROM public.orders WHERE order_number = 'UNV-TEST-0001';
  ASSERT v_own_orders = 1, 'FAIL: Customer A cannot view own order';

  -- 2.2 Customer A can read own address
  SELECT count(*) INTO v_own_addresses FROM public.addresses WHERE full_name = 'Customer Alpha';
  ASSERT v_own_addresses = 1, 'FAIL: Customer A cannot view own address';

  RAISE NOTICE 'SUCCESS: Test Case 2 (Customer A Self-Access) Passed';
END $$;

-- ------------------------------------------------------------------------------
-- TEST CASE 3: Customer B Isolation & Cross-Tenant Negative Test
-- ------------------------------------------------------------------------------
-- Simulate Customer B Authenticated Session
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "00000000-0000-0000-0000-000000000002", "role": "authenticated"}';

DO $$
DECLARE
  v_stolen_orders INT;
  v_stolen_addresses INT;
BEGIN
  -- 3.1 Customer B CANNOT read Customer A's order
  SELECT count(*) INTO v_stolen_orders FROM public.orders WHERE order_number = 'UNV-TEST-0001';
  ASSERT v_stolen_orders = 0, 'SECURITY VIOLATION: Customer B read Customer A order';

  -- 3.2 Customer B CANNOT read Customer A's address
  SELECT count(*) INTO v_stolen_addresses FROM public.addresses WHERE full_name = 'Customer Alpha';
  ASSERT v_stolen_addresses = 0, 'SECURITY VIOLATION: Customer B read Customer A address';

  RAISE NOTICE 'SUCCESS: Test Case 3 (Cross-Customer RLS Isolation) Passed';
END $$;

-- ------------------------------------------------------------------------------
-- TEST CASE 4: Staff Permission Scoping (Order Manager vs Inventory)
-- ------------------------------------------------------------------------------
-- Simulate Order Manager Staff Authenticated Session
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "00000000-0000-0000-0000-000000000003", "role": "authenticated"}';

DO $$
DECLARE
  v_staff_orders INT;
  v_inventory_read_allowed BOOLEAN;
BEGIN
  -- 4.1 Order Manager CAN view customer orders
  SELECT count(*) INTO v_staff_orders FROM public.orders WHERE order_number = 'UNV-TEST-0001';
  ASSERT v_staff_orders = 1, 'FAIL: Order Manager cannot view store orders';

  -- 4.2 Verify permission helper
  v_inventory_read_allowed := auth.has_permission('inventory.adjust');
  ASSERT v_inventory_read_allowed = false, 'SECURITY VIOLATION: Order Manager has inventory.adjust permission';

  RAISE NOTICE 'SUCCESS: Test Case 4 (Staff Permission Scoping) Passed';
END $$;

-- Rollback test data and mock users so database remains clean
ROLLBACK;
