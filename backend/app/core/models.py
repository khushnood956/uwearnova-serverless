"""
Domain Models Registry
Ensures all domain models are loaded into SQLAlchemy DeclarativeBase metadata and mapper registry.
Prevents mapper resolution failures (such as missing relationship targets) during CLI and migration tasks.
"""

from app.core.base import Base

# Import domain models to ensure registration on Base.metadata
from app.modules.auth.models import User, RefreshToken, PasswordReset
from app.modules.rbac.models import Role, Permission, role_permissions, user_roles
from app.modules.audit.models import AuditLog
from app.modules.catalog.models import (
    Category,
    Collection,
    Product,
    ProductImage,
    ProductVariant,
    product_collections,
)
from app.modules.inventory.models import (
    InventoryItem,
    InventoryLocation,
    InventoryMovement,
)
from app.modules.cart.models import (
    Cart,
    CartItem,
    Wishlist,
    WishlistItem,
)
from app.modules.shipping.models import (
    ShippingMethod,
    ShippingZone,
)
from app.modules.orders.models import (
    CheckoutIdempotency,
    Order,
    OrderItem,
    OrderStatusHistory,
)
from app.modules.payments.models import (
    Payment,
    PaymentEvent,
    PaymentTransaction,
    Refund,
)
from app.modules.fulfillment.models import (
    Shipment,
    ShipmentEvent,
    ShipmentItem,
)
from app.modules.returns.models import (
    ReturnItem,
    ReturnRequest,
)
from app.modules.customer.models import (
    Address,
    CustomerProfile,
)
from app.modules.staff.models import (
    StaffProfile,
    StaffTask,
    SupportTicket,
    SupportTicketMessage,
)
from app.modules.promotions.models import (
    Coupon,
    CouponRedemption,
)
from app.modules.reviews.models import (
    ProductReview,
)
from app.modules.content.models import (
    AnnouncementBar,
    ContentPage,
    HomepageCampaign,
)
from app.modules.offline_sales.models import (
    OfflineSale,
    OfflineSaleItem,
)
