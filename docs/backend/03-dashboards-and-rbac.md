# 03 — Dashboards and Role-Based Access Control

## 1. Dashboard surfaces

The application has three primary dashboard surfaces:

1. **Customer account portal**
2. **Staff operations dashboard**
3. **Store administration dashboard**

These are role-based experiences over the same backend, not separate databases or duplicated business logic. A platform-owner/super-admin role is optional and should only be added if the business operates multiple stores or needs a technical platform operator.

## 2. Customer portal

Suggested routes:
- `/account`
- `/account/profile`
- `/account/addresses`
- `/account/orders`
- `/account/orders/[orderNumber]`
- `/account/wishlist`
- `/account/returns`
- `/account/security`

Features:
- Profile and contact details.
- Address book.
- Order history and order detail/timeline.
- Shipment tracking details when available.
- Return/exchange request submission and status.
- Wishlist synchronization for signed-in users.
- Password/session management.
- Communication preferences and consent.

Customer security:
- A customer can access only their own profile, addresses, carts, orders, returns and wishlist.
- Every ownership check is enforced in the API.
- Never rely on a user ID supplied by the browser to authorize record access.

## 3. Store administration dashboard

Suggested routes:
- `/admin`
- `/admin/products`
- `/admin/categories`
- `/admin/collections`
- `/admin/inventory`
- `/admin/orders`
- `/admin/customers`
- `/admin/promotions`
- `/admin/reviews`
- `/admin/returns`
- `/admin/payments`
- `/admin/shipping`
- `/admin/staff`
- `/admin/roles`
- `/admin/content`
- `/admin/reports`
- `/admin/settings`
- `/admin/audit-logs`

### Admin capabilities

**Overview**
- Sales totals and order counts for selectable periods.
- Pending/unfulfilled orders.
- Low-stock alerts.
- Returns awaiting action.
- Payment/COD reconciliation indicators.
- Metrics must be computed from persisted backend data, not hardcoded dashboard numbers.

**Catalogue**
- Create/edit/archive products.
- Manage categories and collections.
- Manage variants, SKU, sizes, colors, prices and media.
- Draft/publish workflow.
- Bulk import/export only after validation and permission design.

**Inventory**
- Stock by variant and location.
- Stock adjustments with reason.
- Movement history.
- Low-stock thresholds.
- No direct unlogged stock mutation.

**Orders**
- Search/filter orders.
- View order and customer snapshots.
- Confirm/cancel according to allowed state transitions.
- Update fulfillment and shipment status.
- Print/export packing details if required.
- Maintain status history.

**Customers**
- Search customers and view account/order history.
- Disable accounts only with explicit permission and audit.
- Do not expose passwords, tokens or payment credentials.

**Payments and shipping**
- View payment states and reconciliation records.
- Manage COD workflow.
- Configure enabled payment/shipping methods.
- Provider credentials are managed through deployment secrets, never displayed in UI.

**Promotions/content**
- Manage coupons and campaign content.
- Validate date ranges, limits and stacking rules on the backend.
- Preview published content.

**Staff and security**
- Create/disable staff accounts.
- Assign roles and permissions.
- View audit history.
- High-risk permission changes require re-authentication or other step-up protection if appropriate.

## 4. Staff operations dashboard

Suggested routes:
- `/staff`
- `/staff/orders`
- `/staff/fulfillment`
- `/staff/inventory`
- `/staff/returns`
- `/staff/customers` (restricted)
- `/staff/support` (if implemented)
- `/staff/profile`

Staff dashboard is a role-filtered work queue, not a second full admin panel.

Suggested staff roles (business may combine roles initially):
- **Order Manager:** view and process orders; confirm/cancel only within policy.
- **Fulfillment Staff:** pick/pack/dispatch and update shipment details.
- **Inventory Manager:** receive stock, adjust quantities with reason, view movement history.
- **Customer Support:** view permitted customer/order data, add internal notes, manage support and return requests.
- **Content/Catalog Editor:** edit product content and media, but cannot change sensitive payment/security settings.
- **Finance/Payments Operator:** view payments, COD reconciliation and permitted refunds; cannot edit catalogue or assign roles.

Do not grant every staff member admin privileges for convenience.

## 5. Permission model

Use permissions such as:
- `dashboard.read`
- `products.read`, `products.create`, `products.update`, `products.archive`, `products.publish`
- `categories.manage`
- `collections.manage`
- `inventory.read`, `inventory.adjust`
- `orders.read`, `orders.update`, `orders.cancel`
- `shipments.manage`
- `customers.read`, `customers.update_status`
- `returns.read`, `returns.review`, `returns.resolve`
- `payments.read`, `payments.reconcile`, `refunds.create`
- `promotions.manage`
- `reviews.moderate`
- `content.manage`
- `staff.read`, `staff.manage`
- `roles.read`, `roles.manage`
- `reports.read`, `reports.export`
- `settings.manage`
- `audit.read`

Define roles by assigning permissions. Backend endpoints must check permissions server-side. Frontend navigation should reflect permissions but is not a security boundary.

## 6. Sensitive actions

Require explicit policy and audit records for:
- Refund approval/creation.
- Manual stock adjustment.
- Order cancellation after fulfillment has started.
- Staff account disablement.
- Role and permission changes.
- Payment configuration changes.
- Exporting customer data.
- Changing order totals or applying manual discounts.

Use least privilege and separate high-risk permissions from routine work.

## 7. Dashboard acceptance criteria

- Customer cannot access another customer's records by changing URL or request IDs.
- Staff sees only permitted navigation and data.
- API rejects unauthorized operations even when called directly.
- Admin actions are auditable.
- Dashboard totals reconcile to source orders/payments for the selected period.
- Empty, loading, error and access-denied states are implemented.
- Mobile/tablet layouts are usable for operational staff.
