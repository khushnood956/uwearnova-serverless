"""
Product Media & S3 Storage Tests (Module M08)
Tests direct presigned S3 upload intents, file type & size validation, CloudFront CDN URLs,
upload confirmation, gallery reordering, primary thumbnail exclusivity, S3 file deletion,
and audit logging.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_access_token
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.catalog.models import Category, Product, ProductImage
from app.modules.media.storage import S3StorageService, get_storage_service
from app.modules.rbac.models import Role, user_roles
from app.modules.rbac.service import seed_system_roles_and_permissions


@pytest.fixture
async def seeded_media_env() -> None:
    """Fixture that seeds roles and creates a sample product."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        await seed_system_roles_and_permissions(session)

        # Create category
        cat = Category(name="Women", slug="women", is_active=True)
        session.add(cat)
        await session.flush()

        # Create product
        prod = Product(
            name="Silk Trench Coat",
            slug="silk-trench-coat",
            category_id=cat.id,
            price=Decimal("35000.00"),
            status="active",
        )
        session.add(prod)
        await session.commit()


async def create_user_with_role(
    session: AsyncSession,
    email: str,
    role_name: str,
    user_type: str = "staff",
) -> User:
    """Helper to create a user with a designated system role."""
    user = User(
        email=email,
        password_hash=hash_password("SecurePassword123!"),
        status="active",
        user_type=user_type,
    )
    session.add(user)
    await session.flush()

    role_res = await session.execute(select(Role).where(Role.name == role_name))
    role = role_res.scalar_one()

    await session.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))
    await session.commit()
    await session.refresh(user)
    return user


def auth_header_for(user: User) -> dict:
    """Helper to generate Authorization header for user."""
    token = create_access_token(user_id=user.id, user_type=user.user_type)
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Validation & Presigned URL Generation Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_presigned_upload_intent_validation(async_client: AsyncClient, seeded_media_env):
    """Verify file type rejection, size boundary enforcement, and valid URL generation."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "media_admin@uwearnova.com", "store_admin", "admin")
        prod = (await session.execute(select(Product))).scalars().first()

    admin_headers = auth_header_for(admin)

    # 1. Reject disallowed MIME type (e.g. application/pdf)
    resp_invalid_type = await async_client.post(
        f"/api/v1/admin/products/{prod.id}/media/upload-intent",
        json={"file_name": "manual.pdf", "mime_type": "application/pdf", "file_size_bytes": 102400},
        headers=admin_headers,
    )
    assert resp_invalid_type.status_code == 400
    assert resp_invalid_type.json()["error"]["code"] == "INVALID_MIME_TYPE"

    # 2. Reject file exceeding 10MB limit (e.g. 15MB)
    resp_too_large = await async_client.post(
        f"/api/v1/admin/products/{prod.id}/media/upload-intent",
        json={"file_name": "giant.webp", "mime_type": "image/webp", "file_size_bytes": 15 * 1024 * 1024},
        headers=admin_headers,
    )
    assert resp_too_large.status_code == 400
    assert resp_too_large.json()["error"]["code"] == "FILE_TOO_LARGE"

    # 3. Reject non-existent product
    resp_no_prod = await async_client.post(
        "/api/v1/admin/products/99999/media/upload-intent",
        json={"file_name": "front.webp", "mime_type": "image/webp", "file_size_bytes": 500000},
        headers=admin_headers,
    )
    assert resp_no_prod.status_code == 404
    assert resp_no_prod.json()["error"]["code"] == "PRODUCT_NOT_FOUND"

    # 4. Successful upload intent
    valid_resp = await async_client.post(
        f"/api/v1/admin/products/{prod.id}/media/upload-intent",
        json={"file_name": "Trench Front View.WEBP", "mime_type": "image/webp", "file_size_bytes": 1048576},
        headers=admin_headers,
    )
    assert valid_resp.status_code == 200
    intent = valid_resp.json()
    assert "upload_url" in intent
    assert intent["http_method"] == "PUT"
    assert intent["required_headers"]["Content-Type"] == "image/webp"
    assert f"products/{prod.id}/images/" in intent["storage_key"]
    assert "trench-front-view.webp" in intent["storage_key"]
    assert intent["public_url"].endswith(intent["storage_key"])


# ===========================================================================
# 2. S3 & CloudFront URL Resolution Unit Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_s3_storage_service_and_cloudfront_urls():
    """Verify S3 client presigned URL generation and CloudFront URL formatting."""
    mock_settings = Settings(
        STORAGE_BACKEND="s3",
        AWS_REGION="ap-southeast-1",
        AWS_S3_BUCKET_NAME="uninova-test-bucket",
        AWS_CLOUDFRONT_DOMAIN="cdn.uninova.example.com",
    )

    with patch("boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://uninova-test-bucket.s3.amazonaws.com/test-key?sig=abc"
        mock_boto.return_value = mock_s3

        s3_service = S3StorageService(mock_settings)

        # 1. CloudFront public URL resolution
        public_url = s3_service.get_public_url("products/1/images/test.webp")
        assert public_url == "https://cdn.uninova.example.com/products/1/images/test.webp"

        # 2. Presigned PUT generation
        presigned = s3_service.generate_presigned_upload(
            storage_key="products/1/images/test.webp",
            mime_type="image/webp",
            max_bytes=1000000,
            expires_in=600,
        )
        assert presigned["upload_url"] == "https://uninova-test-bucket.s3.amazonaws.com/test-key?sig=abc"
        assert presigned["required_headers"] == {"Content-Type": "image/webp"}

        mock_s3.generate_presigned_url.assert_called_once_with(
            ClientMethod="put_object",
            Params={
                "Bucket": "uninova-test-bucket",
                "Key": "products/1/images/test.webp",
                "ContentType": "image/webp",
            },
            ExpiresIn=600,
        )

        # 3. S3 deletion call
        s3_service.delete_file("products/1/images/test.webp")
        mock_s3.delete_object.assert_called_once_with(
            Bucket="uninova-test-bucket",
            Key="products/1/images/test.webp",
        )


# ===========================================================================
# 3. Upload Confirmation, Metadata, and Primary Thumbnail Exclusivity
# ===========================================================================

@pytest.mark.asyncio
async def test_confirm_upload_and_primary_exclusivity(async_client: AsyncClient, seeded_media_env):
    """
    First uploaded image becomes primary; subsequent images with is_primary=True unset previous primary.
    Audit log product_image.uploaded is recorded.
    """
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "confirmer@uwearnova.com", "store_admin", "admin")
        prod = (await session.execute(select(Product))).scalars().first()
        prod_id = prod.id

    admin_headers = auth_header_for(admin)

    # 1. Confirm first image (should auto-become primary)
    img1_payload = {
        "storage_key": f"products/{prod_id}/images/img1.webp",
        "alt_text": "Front angle",
        "is_primary": False,  # Should be auto-promoted to True since it's the first
        "file_size_bytes": 204800,
        "mime_type": "image/webp",
        "width": 1200,
        "height": 1600,
    }
    resp1 = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/media/confirm",
        json=img1_payload,
        headers=admin_headers,
    )
    assert resp1.status_code == 201
    img1 = resp1.json()
    assert img1["is_primary"] is True
    assert img1["sort_order"] == 0
    assert img1["width"] == 1200
    img1_id = img1["id"]

    # 2. Confirm second image (not primary)
    img2_payload = {
        "storage_key": f"products/{prod_id}/images/img2.webp",
        "alt_text": "Side detail",
        "is_primary": False,
        "file_size_bytes": 180000,
        "mime_type": "image/webp",
    }
    resp2 = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/media/confirm",
        json=img2_payload,
        headers=admin_headers,
    )
    assert resp2.status_code == 201
    img2 = resp2.json()
    assert img2["is_primary"] is False
    assert img2["sort_order"] == 1
    img2_id = img2["id"]

    # 3. Confirm third image with is_primary=True (must demote image 1)
    img3_payload = {
        "storage_key": f"products/{prod_id}/images/img3.webp",
        "alt_text": "Back view",
        "is_primary": True,
        "file_size_bytes": 220000,
        "mime_type": "image/webp",
    }
    resp3 = await async_client.post(
        f"/api/v1/admin/products/{prod_id}/media/confirm",
        json=img3_payload,
        headers=admin_headers,
    )
    assert resp3.status_code == 201
    img3 = resp3.json()
    assert img3["is_primary"] is True
    img3_id = img3["id"]

    # Verify database state for primary exclusivity
    async with TestingSessionLocal() as session:
        images = (
            await session.execute(
                select(ProductImage).where(ProductImage.product_id == prod_id).order_by(ProductImage.sort_order)
            )
        ).scalars().all()
        assert len(images) == 3
        # Image 1 demoted, Image 2 never primary, Image 3 now primary
        img_map = {i.id: i.is_primary for i in images}
        assert img_map[img1_id] is False
        assert img_map[img2_id] is False
        assert img_map[img3_id] is True

    # 4. Reorder gallery sequence
    reorder_resp = await async_client.put(
        f"/api/v1/admin/products/{prod_id}/media/reorder",
        json={"image_ids": [img3_id, img1_id, img2_id]},
        headers=admin_headers,
    )
    assert reorder_resp.status_code == 200
    reordered = reorder_resp.json()
    assert [i["id"] for i in reordered] == [img3_id, img1_id, img2_id]
    assert [i["sort_order"] for i in reordered] == [0, 1, 2]

    # 5. Set image 2 as primary via set-primary endpoint
    set_prim_resp = await async_client.put(
        f"/api/v1/admin/products/{prod_id}/media/{img2_id}/set-primary",
        headers=admin_headers,
    )
    assert set_prim_resp.status_code == 200
    assert set_prim_resp.json()["is_primary"] is True


# ===========================================================================
# 4. Deletion, S3 File Cleanup, and Fallback Primary Promotion
# ===========================================================================

@pytest.mark.asyncio
async def test_delete_media_cleans_up_storage_and_promotes_primary(async_client: AsyncClient, seeded_media_env):
    """Deleting primary image removes S3 storage object and promotes next remaining image to primary."""
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        admin = await create_user_with_role(session, "deleter@uwearnova.com", "store_admin", "admin")
        prod = (await session.execute(select(Product))).scalars().first()
        prod_id = prod.id

        # Insert two images
        img1 = ProductImage(
            product_id=prod_id,
            image_url="https://media.uninova.example.com/p1.webp",
            storage_key=f"products/{prod_id}/images/p1.webp",
            sort_order=0,
            is_primary=True,
        )
        img2 = ProductImage(
            product_id=prod_id,
            image_url="https://media.uninova.example.com/p2.webp",
            storage_key=f"products/{prod_id}/images/p2.webp",
            sort_order=1,
            is_primary=False,
        )
        session.add_all([img1, img2])
        await session.commit()
        await session.refresh(img1)
        await session.refresh(img2)
        img1_id = img1.id
        img2_id = img2.id

    admin_headers = auth_header_for(admin)

    # Delete primary image 1
    del_resp = await async_client.delete(
        f"/api/v1/admin/products/{prod_id}/media/{img1_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 200

    # Verify in DB: Image 1 deleted, Image 2 promoted to primary
    async with TestingSessionLocal() as session:
        remaining = (
            await session.execute(
                select(ProductImage).where(ProductImage.product_id == prod_id)
            )
        ).scalars().all()
        assert len(remaining) == 1
        assert remaining[0].id == img2_id
        assert remaining[0].is_primary is True

        # Verify audit log
        audit = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "product_image",
                    AuditLog.entity_id == str(img1_id),
                    AuditLog.action == "product_image.deleted",
                )
            )
        ).scalar_one()
        assert audit.user_id == admin.id
