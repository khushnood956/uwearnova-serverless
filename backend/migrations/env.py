import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure app directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.base import Base
from app.core.config import get_settings
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

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set model metadata for autogenerate support
target_metadata = Base.metadata

# Retrieve dynamic database connection URL
settings = get_settings()
db_url = os.getenv("ALEMBIC_DATABASE_URL") or settings.sync_database_url
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode generating SQL scripts."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode connecting directly to the database."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
