# 02 — MySQL Database Design

## 1. Principles

Use MySQL 8.0-compatible InnoDB tables, foreign keys, explicit indexes and migrations. The schema below is a domain blueprint, not permission to create every table in the first migration. Implement entities module by module.

Use:
- `BIGINT` or a consistent UUID strategy for primary keys. Choose one strategy project-wide before migrations.
- `DECIMAL`, never `FLOAT`/`DOUBLE`, for monetary values.
- UTC timestamps.
- Explicit status columns with controlled application enums or lookup tables.
- Soft deletion only where justified; do not soft-delete transactional records indiscriminately.
- Unique constraints for business identifiers such as SKU, email (subject to case-normalization policy), order number and provider event ID.

## 2. Core identity and access

### users
- id
- email
- password_hash
- phone
- status (`active`, `pending_verification`, `disabled`, `locked`)
- email_verified_at
- last_login_at
- created_at, updated_at

### customer_profiles
- id, user_id (unique FK)
- first_name, last_name
- marketing_consent_at (nullable)
- created_at, updated_at

### staff_profiles
- id, user_id (unique FK)
- employee_code (unique)
- display_name
- status
- created_at, updated_at

### roles, permissions, role_permissions, user_roles
Use role-to-permission mapping rather than hardcoding role checks throughout the code. Support assigning multiple roles only if required; otherwise enforce one primary role with granular permissions.

### sessions / refresh_tokens
Persist revocable session or refresh-token metadata if the selected authentication design requires it. Store token hashes, not raw refresh tokens.

### addresses
- id, user_id
- recipient_name, phone
- address_line_1, address_line_2
- city, area, postal_code, country_code
- is_default
- created_at, updated_at

## 3. Catalogue

### categories
- id, parent_id nullable
- name, slug, description
- image_key
- sort_order, is_active

### products
- id, name, slug, description
- brand_label (optional)
- status (`draft`, `active`, `archived`)
- category_id (or product-category join table if products can belong to multiple categories)
- created_at, updated_at, published_at

### product_variants
- id, product_id
- sku (unique)
- size, color_name, color_code
- price, compare_at_price (nullable)
- weight_grams (nullable)
- is_active

### product_media
- id, product_id, variant_id nullable
- storage_key, alt_text, sort_order
- media_type
- is_primary

### product_attributes / product_attribute_values
Use only if the catalogue needs flexible attributes beyond size and color. Avoid premature generic EAV complexity.

### collections / collection_products
For curated storefront collections such as New Arrivals and Signature Collection.

### product_categories
Use if multi-category assignment is required. Do not duplicate category ownership in two conflicting places.

## 4. Inventory

### inventory_locations
A default warehouse/store location can be created initially, while retaining the ability to add locations later.

### inventory_items
- id, variant_id, location_id
- quantity_on_hand
- quantity_reserved
- reorder_threshold
- updated_at
- unique(variant_id, location_id)

Available quantity = quantity_on_hand - quantity_reserved. Enforce non-negative quantities through transactional service logic and database constraints where supported.

### inventory_movements
- id, variant_id, location_id
- movement_type (`receipt`, `sale`, `reservation`, `release`, `return`, `adjustment`)
- quantity_delta
- reference_type, reference_id
- created_by_user_id
- created_at

Do not rely only on a mutable stock number; preserve a movement history.

## 5. Cart and wishlist

### carts
- id, user_id nullable
- anonymous_cart_key nullable
- status
- created_at, updated_at

### cart_items
- id, cart_id, variant_id
- quantity
- unique(cart_id, variant_id)

### wishlists / wishlist_items
Support authenticated users first. Guest wishlist persistence can remain client-side in the initial release unless a product requirement demands server sync.

The backend must validate current price and availability during checkout; cart prices are not authoritative.

## 6. Orders and checkout

### orders
- id, order_number (unique)
- user_id nullable for supported guest checkout
- status
- payment_status
- fulfillment_status
- currency_code
- subtotal, discount_total, shipping_total, tax_total, grand_total
- shipping_address_snapshot
- billing_address_snapshot nullable
- customer_note nullable
- placed_at, created_at, updated_at

### order_items
Store immutable purchase snapshots:
- id, order_id
- product_id nullable FK
- variant_id nullable FK
- sku_snapshot, product_name_snapshot
- size_snapshot, color_snapshot
- unit_price, quantity, line_discount, line_total
- weight_snapshot_grams nullable

Historical orders must remain readable even if catalogue items are renamed, archived or deleted.

### order_status_history
- id, order_id
- from_status, to_status
- note
- changed_by_user_id nullable
- created_at

### checkout_idempotency
Store idempotency key, request fingerprint, resulting order reference and expiry/retention policy to prevent duplicate order creation.

## 7. Payments and refunds

### payments
- id, order_id
- provider_code (`cod` or configured provider key)
- provider_reference nullable
- amount, currency_code
- status
- initiated_at, confirmed_at nullable

### payment_events
- id, payment_id nullable
- provider_event_id unique where available
- event_type
- signature_verified
- payload_reference or carefully redacted payload
- processed_at
- processing_status

### refunds
- id, order_id, payment_id
- amount, reason, status
- provider_reference nullable
- created_by_user_id
- created_at, completed_at nullable

Do not store payment-card numbers, CVV or raw authentication credentials.

## 8. Shipping and returns

### shipping_methods
Configurable service name, price/rules, COD support and enabled state.

### shipments
- id, order_id
- courier_code
- tracking_number
- status
- shipped_at, delivered_at nullable

### shipment_events
Normalized tracking updates with source and event time.

### return_requests
- id, order_id, user_id
- request_type (`return`, `exchange`)
- reason, customer_note
- status
- resolution
- created_at, updated_at

### return_items
Requested order-item quantities and exchange variant references.

## 9. Promotions, reviews and content

Potential tables:
- coupons
- coupon_redemptions
- promotion_rules (only if rules become more complex)
- product_reviews
- review_media (optional)
- content_pages
- homepage_campaigns
- announcement_bars

Implement only those required by the agreed release scope.

## 10. Operations, communication and audit

Potential tables:
- notification_templates
- notification_outbox
- admin_audit_logs
- support_tickets (if support workflow is in scope)
- settings (typed settings are preferable to an unstructured key/value dump)

Audit records should capture actor, action, target, timestamp and a safe before/after summary. Do not put secrets or unnecessary personal data into audit payloads.

## 11. Critical transaction boundaries

1. **Place order:** validate cart, re-price items, validate stock, create order and item snapshots, reserve/decrement inventory consistently, create payment record, commit once.
2. **Payment webhook:** verify signature, deduplicate event, update payment/order state in a transaction.
3. **Cancel order:** validate current state, release eligible reservations, record history.
4. **Return restock:** only restock after the defined physical/operational return checkpoint; record movement.
5. **Admin stock adjustment:** require permission, reason and audit/movement record.

The exact reservation policy (reserve at checkout vs confirm after order verification) must be decided and documented before implementing checkout/inventory transactions.
