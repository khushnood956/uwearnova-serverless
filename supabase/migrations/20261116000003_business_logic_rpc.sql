-- ==============================================================================
-- UniNova E-Commerce: High-Concurrency Atomic Business Operations (RPC)
-- Migration: 20261116000003_business_logic_rpc.sql
-- Description: Stored procedures & RPC functions guaranteeing ACID guarantees
--              for checkout, inventory deduction, cart merging, coupon validation,
--              and POS offline sales.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Atomic Checkout & Order Placement RPC
-- ------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.place_order_atomic(p_order_data JSONB)
RETURNS JSONB AS $$
DECLARE
  v_user_id BIGINT;
  v_order_id BIGINT;
  v_order_number TEXT;
  v_item JSONB;
  v_variant_id BIGINT;
  v_qty INT;
  v_price NUMERIC(12,2);
  v_stock INT;
  v_subtotal NUMERIC(12,2) := 0.00;
  v_shipping NUMERIC(12,2) := 350.00;
  v_discount NUMERIC(12,2) := 0.00;
  v_grand_total NUMERIC(12,2);
  v_payment_method TEXT;
  v_idempotency_key TEXT;
  v_existing_order JSONB;
  v_inv_item_id BIGINT;
BEGIN
  -- 1. Check idempotency if key provided
  v_idempotency_key := p_order_data->>'idempotency_key';
  IF v_idempotency_key IS NOT NULL THEN
    SELECT response_payload INTO v_existing_order
    FROM public.checkout_idempotency
    WHERE idempotency_key = v_idempotency_key
      AND expires_at > now();

    IF v_existing_order IS NOT NULL THEN
      RETURN v_existing_order;
    END IF;
  END IF;

  -- 2. Resolve caller user ID (NULL for guest checkout)
  v_user_id := auth.current_domain_user_id();

  -- 3. Generate unique order number (UNV-YYYYMMDD-XXXXXX)
  v_order_number := 'UNV-' || to_char(now(), 'YYYYMMDD') || '-' || upper(substr(md5(random()::text), 1, 6));

  -- 4. Calculate or verify shipping fee
  IF (p_order_data->>'shipping_fee') IS NOT NULL THEN
    v_shipping := (p_order_data->>'shipping_fee')::NUMERIC(12,2);
  END IF;

  -- Verify discount if coupon applied
  IF (p_order_data->>'discount_amount') IS NOT NULL THEN
    v_discount := (p_order_data->>'discount_amount')::NUMERIC(12,2);
  END IF;

  v_payment_method := COALESCE(p_order_data->>'payment_method', 'cod');

  -- 5. Insert initial order header
  INSERT INTO public.orders (
    order_number,
    user_id,
    customer_email,
    customer_phone,
    customer_name,
    status,
    payment_status,
    fulfillment_status,
    payment_method,
    currency_code,
    subtotal,
    discount_amount,
    shipping_fee,
    grand_total,
    shipping_method_code,
    shipping_method_name,
    shipping_address,
    customer_note,
    placed_at
  ) VALUES (
    v_order_number,
    v_user_id,
    p_order_data->>'customer_email',
    p_order_data->>'customer_phone',
    p_order_data->>'customer_name',
    'pending_confirmation',
    'unpaid',
    'unfulfilled',
    v_payment_method,
    'PKR',
    0.00,
    v_discount,
    v_shipping,
    0.00,
    COALESCE(p_order_data->>'shipping_method_code', 'standard'),
    COALESCE(p_order_data->>'shipping_method_name', 'Standard Delivery'),
    p_order_data->'shipping_address',
    p_order_data->>'customer_note',
    now()
  ) RETURNING id INTO v_order_id;

  -- 6. Lock and Deduct Inventory for Each Line Item
  FOR v_item IN SELECT * FROM jsonb_array_elements(p_order_data->'items')
  LOOP
    v_variant_id := (v_item->>'variant_id')::BIGINT;
    v_qty := (v_item->>'quantity')::INT;

    IF v_qty <= 0 THEN
      RAISE EXCEPTION 'INVALID_QUANTITY: Line item quantity must be greater than 0';
    END IF;

    -- Lock variant row and retrieve trusted database price and stock
    SELECT price, inventory_count INTO v_price, v_stock
    FROM public.product_variants
    WHERE id = v_variant_id
    FOR UPDATE;

    IF NOT FOUND THEN
      RAISE EXCEPTION 'VARIANT_NOT_FOUND: Product variant % does not exist', v_variant_id;
    END IF;

    IF v_stock < v_qty THEN
      RAISE EXCEPTION 'INSUFFICIENT_STOCK: Variant % has only % units remaining (requested %)', v_variant_id, v_stock, v_qty;
    END IF;

    -- Atomic stock deduction
    UPDATE public.product_variants
    SET inventory_count = inventory_count - v_qty
    WHERE id = v_variant_id;

    -- Update inventory_items if warehouse facility record exists
    SELECT id INTO v_inv_item_id
    FROM public.inventory_items
    WHERE variant_id = v_variant_id
    LIMIT 1;

    IF v_inv_item_id IS NOT NULL THEN
      UPDATE public.inventory_items
      SET quantity_on_hand = quantity_on_hand - v_qty
      WHERE id = v_inv_item_id;

      INSERT INTO public.inventory_movements (
        inventory_item_id,
        movement_type,
        quantity,
        reference_type,
        reference_id,
        notes,
        created_by_user_id
      ) VALUES (
        v_inv_item_id,
        'sale_deduction',
        -v_qty,
        'order',
        v_order_number,
        'Deducted during checkout order ' || v_order_number,
        v_user_id
      );
    END IF;

    -- Insert snapshot line item
    INSERT INTO public.order_items (
      order_id,
      variant_id,
      product_name,
      product_slug,
      sku,
      size,
      color,
      unit_price,
      quantity,
      line_discount,
      line_total,
      image_url
    ) VALUES (
      v_order_id,
      v_variant_id,
      v_item->>'product_name',
      v_item->>'product_slug',
      v_item->>'sku',
      v_item->>'size',
      v_item->>'color',
      v_price,
      v_qty,
      0.00,
      (v_price * v_qty),
      v_item->>'image_url'
    );

    v_subtotal := v_subtotal + (v_price * v_qty);
  END LOOP;

  -- 7. Calculate Grand Total
  v_grand_total := GREATEST(0.00, (v_subtotal - v_discount)) + v_shipping;

  UPDATE public.orders
  SET subtotal = v_subtotal,
      grand_total = v_grand_total
  WHERE id = v_order_id;

  -- 8. Record Status History
  INSERT INTO public.order_status_history (
    order_id,
    from_status,
    to_status,
    notes,
    created_by_user_id
  ) VALUES (
    v_order_id,
    'none',
    'pending_confirmation',
    'Order placed online via storefront checkout.',
    v_user_id
  );

  -- 9. Create Payment Record (COD or gateway session)
  INSERT INTO public.payments (
    order_id,
    provider_code,
    payment_method,
    status,
    amount,
    currency_code
  ) VALUES (
    v_order_id,
    v_payment_method,
    v_payment_method,
    'pending',
    v_grand_total,
    'PKR'
  );

  -- 10. Clear Shopping Cart if cart ID provided
  IF (p_order_data->>'cart_id') IS NOT NULL THEN
    DELETE FROM public.cart_items WHERE cart_id = (p_order_data->>'cart_id')::BIGINT;
  END IF;

  -- 11. Build Response Object
  v_existing_order := jsonb_build_object(
    'order_id', v_order_id,
    'order_number', v_order_number,
    'status', 'pending_confirmation',
    'subtotal', v_subtotal,
    'shipping_fee', v_shipping,
    'discount_amount', v_discount,
    'grand_total', v_grand_total,
    'customer_email', p_order_data->>'customer_email'
  );

  -- 12. Save Idempotency Cache if requested
  IF v_idempotency_key IS NOT NULL THEN
    INSERT INTO public.checkout_idempotency (
      idempotency_key,
      order_id,
      request_hash,
      response_payload,
      expires_at
    ) VALUES (
      v_idempotency_key,
      v_order_id,
      md5(p_order_data::text),
      v_existing_order,
      now() + interval '24 hours'
    );
  END IF;

  RETURN v_existing_order;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- ------------------------------------------------------------------------------
-- 2. Guest Cart Merge RPC on Customer Login
-- ------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.merge_guest_cart(p_anon_token TEXT)
RETURNS JSONB AS $$
DECLARE
  v_user_id BIGINT;
  v_guest_cart_id BIGINT;
  v_user_cart_id BIGINT;
  v_item RECORD;
BEGIN
  v_user_id := auth.current_domain_user_id();
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'AUTHENTICATION_REQUIRED: Caller must be logged in to merge carts';
  END IF;

  -- Find guest cart
  SELECT id INTO v_guest_cart_id
  FROM public.carts
  WHERE anonymous_token = p_anon_token;

  IF v_guest_cart_id IS NULL THEN
    RETURN jsonb_build_object('merged', false, 'reason', 'No guest cart found for token');
  END IF;

  -- Find or create customer cart
  SELECT id INTO v_user_cart_id
  FROM public.carts
  WHERE user_id = v_user_id;

  IF v_user_cart_id IS NULL THEN
    -- Reassign guest cart directly to user
    UPDATE public.carts
    SET user_id = v_user_id,
        anonymous_token = NULL
    WHERE id = v_guest_cart_id;
    RETURN jsonb_build_object('merged', true, 'reassigned', true);
  END IF;

  -- Move items from guest cart to user cart
  FOR v_item IN SELECT * FROM public.cart_items WHERE cart_id = v_guest_cart_id
  LOOP
    INSERT INTO public.cart_items (cart_id, variant_id, quantity)
    VALUES (v_user_cart_id, v_item.variant_id, v_item.quantity)
    ON CONFLICT (cart_id, variant_id)
    DO UPDATE SET quantity = cart_items.quantity + EXCLUDED.quantity;
  END LOOP;

  -- Remove old guest cart
  DELETE FROM public.carts WHERE id = v_guest_cart_id;

  RETURN jsonb_build_object('merged', true, 'target_cart_id', v_user_cart_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- ------------------------------------------------------------------------------
-- 3. Coupon Validation RPC
-- ------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.validate_and_apply_coupon(
  p_code TEXT,
  p_subtotal NUMERIC
)
RETURNS JSONB AS $$
DECLARE
  v_coupon RECORD;
  v_discount NUMERIC(12,2) := 0.00;
BEGIN
  SELECT * INTO v_coupon
  FROM public.coupons
  WHERE code = upper(trim(p_code))
    AND is_active = true;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('valid', false, 'message', 'Coupon code is invalid or inactive');
  END IF;

  IF v_coupon.valid_from > now() THEN
    RETURN jsonb_build_object('valid', false, 'message', 'Coupon is not yet active');
  END IF;

  IF v_coupon.valid_until IS NOT NULL AND v_coupon.valid_until < now() THEN
    RETURN jsonb_build_object('valid', false, 'message', 'Coupon has expired');
  END IF;

  IF v_coupon.usage_limit IS NOT NULL AND v_coupon.usage_count >= v_coupon.usage_limit THEN
    RETURN jsonb_build_object('valid', false, 'message', 'Coupon usage limit has been reached');
  END IF;

  IF p_subtotal < v_coupon.minimum_order_amount THEN
    RETURN jsonb_build_object(
      'valid', false,
      'message', 'Minimum order amount for this coupon is PKR ' || v_coupon.minimum_order_amount
    );
  END IF;

  -- Calculate discount
  IF v_coupon.discount_type = 'percentage' THEN
    v_discount := ROUND((p_subtotal * (v_coupon.discount_value / 100.0)), 2);
  ELSE
    v_discount := LEAST(v_coupon.discount_value, p_subtotal);
  END IF;

  RETURN jsonb_build_object(
    'valid', true,
    'code', v_coupon.code,
    'discount_type', v_coupon.discount_type,
    'discount_value', v_coupon.discount_value,
    'discount_amount', v_discount
  );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- ------------------------------------------------------------------------------
-- 4. POS Offline Walk-in Sale RPC
-- ------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.create_offline_sale(p_sale_data JSONB)
RETURNS JSONB AS $$
DECLARE
  v_sale_id BIGINT;
  v_receipt_number TEXT;
  v_item JSONB;
  v_variant_id BIGINT;
  v_qty INT;
  v_price NUMERIC(12,2);
  v_stock INT;
  v_total NUMERIC(12,2) := 0.00;
  v_staff_id BIGINT;
BEGIN
  -- Resolve staff profile
  SELECT sp.id INTO v_staff_id
  FROM public.staff_profiles sp
  JOIN public.users u ON sp.user_id = u.id
  WHERE u.auth_user_id = auth.uid()
  LIMIT 1;

  v_receipt_number := 'POS-' || to_char(now(), 'YYYYMMDD') || '-' || upper(substr(md5(random()::text), 1, 6));

  INSERT INTO public.offline_sales (
    receipt_number,
    staff_id,
    customer_name,
    customer_phone,
    customer_email,
    payment_method,
    total_amount,
    status
  ) VALUES (
    v_receipt_number,
    v_staff_id,
    p_sale_data->>'customer_name',
    p_sale_data->>'customer_phone',
    p_sale_data->>'customer_email',
    COALESCE(p_sale_data->>'payment_method', 'cash'),
    0.00,
    'completed'
  ) RETURNING id INTO v_sale_id;

  -- Process line items
  FOR v_item IN SELECT * FROM jsonb_array_elements(p_sale_data->'items')
  LOOP
    v_variant_id := (v_item->>'variant_id')::BIGINT;
    v_qty := (v_item->>'quantity')::INT;

    -- Lock and check stock
    SELECT price, inventory_count INTO v_price, v_stock
    FROM public.product_variants
    WHERE id = v_variant_id
    FOR UPDATE;

    IF v_stock < v_qty THEN
      RAISE EXCEPTION 'INSUFFICIENT_STOCK: POS item % has only % stock', v_variant_id, v_stock;
    END IF;

    -- Deduct stock
    UPDATE public.product_variants
    SET inventory_count = inventory_count - v_qty
    WHERE id = v_variant_id;

    -- Custom price override or standard price
    IF (v_item->>'unit_price') IS NOT NULL THEN
      v_price := (v_item->>'unit_price')::NUMERIC(12,2);
    END IF;

    INSERT INTO public.offline_sale_items (
      sale_id,
      variant_id,
      unit_price,
      quantity,
      line_total
    ) VALUES (
      v_sale_id,
      v_variant_id,
      v_price,
      v_qty,
      (v_price * v_qty)
    );

    v_total := v_total + (v_price * v_qty);
  END LOOP;

  UPDATE public.offline_sales
  SET total_amount = v_total
  WHERE id = v_sale_id;

  RETURN jsonb_build_object(
    'sale_id', v_sale_id,
    'receipt_number', v_receipt_number,
    'total_amount', v_total
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, auth, pg_temp;

-- ------------------------------------------------------------------------------
-- 5. Analytical Views for Admin Reporting
-- ------------------------------------------------------------------------------

CREATE OR REPLACE VIEW public.v_admin_sales_overview AS
SELECT
  COALESCE(SUM(grand_total), 0.00) AS gross_sales,
  COALESCE(SUM(CASE WHEN payment_status = 'paid' THEN grand_total ELSE 0.00 END), 0.00) AS collected_revenue,
  COALESCE(SUM(CASE WHEN payment_method = 'cod' AND payment_status = 'unpaid' THEN grand_total ELSE 0.00 END), 0.00) AS outstanding_cod,
  COUNT(id) AS total_orders,
  COUNT(CASE WHEN status = 'pending_confirmation' THEN 1 END) AS pending_orders,
  COUNT(CASE WHEN status = 'delivered' THEN 1 END) AS completed_orders,
  COUNT(CASE WHEN status = 'cancelled' THEN 1 END) AS cancelled_orders
FROM public.orders;

CREATE OR REPLACE VIEW public.v_low_stock_alerts AS
SELECT
  p.name AS product_name,
  pv.sku,
  pv.size,
  pv.color_name,
  pv.inventory_count,
  pv.price
FROM public.product_variants pv
JOIN public.products p ON pv.product_id = p.id
WHERE pv.inventory_count <= 5
  AND pv.is_active = true
ORDER BY pv.inventory_count ASC;
