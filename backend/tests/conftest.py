"""
Pytest Test Fixtures
Configures an isolated in-memory test database and async HTTP test client.
"""

import os
# Ensure test environment is established before app configuration loads
os.environ.setdefault("APP_ENV", "test")

from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.base import Base
from app.core.database import get_db
from app.main import app
# Ensure domain models are imported so metadata knows about all tables
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

# Isolated in-memory async SQLite test engine
test_async_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
async def setup_test_database():
    """Create all tables before each test and drop them afterwards for complete isolation."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override providing an isolated test session."""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client against the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
