"""
Product Media Service Layer
Orchestrates presigned S3 upload generation, metadata persistence, CloudFront URLs,
image reordering, primary thumbnail management, and S3 file deletion.
"""

import os
from pathlib import Path
from typing import List, Optional
import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import AppException
from app.core.config import get_settings
from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.catalog.models import Product, ProductImage
from app.modules.catalog.schemas import (
    ConfirmUploadRequest,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.modules.media.storage import get_storage_service, sanitize_filename


async def request_product_image_upload(
    db: AsyncSession,
    product_id: int,
    req: PresignedUploadRequest,
    actor_user: User,
) -> PresignedUploadResponse:
    """Validate upload intent and generate secure short-lived presigned PUT URL."""
    settings = get_settings()

    # 1. Verify product existence
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    # 2. Validate MIME type
    normalized_mime = req.mime_type.strip().lower()
    if normalized_mime not in [m.lower() for m in settings.MEDIA_ALLOWED_MIME_TYPES]:
        allowed = ", ".join(settings.MEDIA_ALLOWED_MIME_TYPES)
        raise AppException(
            message=f"Unsupported file type '{req.mime_type}'. Allowed types: {allowed}",
            code="INVALID_MIME_TYPE",
            status_code=400,
        )

    # 3. Validate file size
    if req.file_size_bytes > settings.MEDIA_UPLOAD_MAX_BYTES:
        max_mb = settings.MEDIA_UPLOAD_MAX_BYTES / (1024 * 1024)
        raise AppException(
            message=f"File size exceeds maximum permitted limit of {max_mb:.0f} MB.",
            code="FILE_TOO_LARGE",
            status_code=400,
        )

    # 4. Partition storage key by product ID and random token to prevent collisions/tampering
    key_token = uuid.uuid4().hex[:12]
    clean_filename = sanitize_filename(req.file_name)
    storage_key = f"products/{product_id}/images/{key_token}-{clean_filename}"

    # 5. Generate presigned URL via storage service
    storage_service = get_storage_service(settings)
    presigned = storage_service.generate_presigned_upload(
        storage_key=storage_key,
        mime_type=normalized_mime,
        max_bytes=req.file_size_bytes,
        expires_in=settings.PRESIGNED_URL_EXPIRE_SECONDS,
    )

    return PresignedUploadResponse(**presigned)


async def confirm_product_image_upload(
    db: AsyncSession,
    product_id: int,
    req: ConfirmUploadRequest,
    actor_user: User,
) -> ProductImage:
    """
    Finalize direct client upload: verify product, register metadata, ensure primary exclusivity,
    and persist image record.
    """
    settings = get_settings()
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    # Check existing images count
    count_res = await db.execute(
        select(func.count(ProductImage.id)).where(ProductImage.product_id == product_id)
    )
    existing_count = count_res.scalar() or 0

    # Auto-assign primary if this is the product's first image
    is_primary = req.is_primary or (existing_count == 0)

    # If this image is primary, unset is_primary on existing images
    if is_primary:
        await db.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_primary=False)
        )

    # Compute sort_order (place at end of gallery)
    max_order_res = await db.execute(
        select(func.max(ProductImage.sort_order)).where(ProductImage.product_id == product_id)
    )
    max_order = max_order_res.scalar()
    next_order = (max_order + 1) if max_order is not None else 0

    # Resolve public CloudFront or S3 URL
    storage_service = get_storage_service(settings)
    public_url = storage_service.get_public_url(req.storage_key)

    image = ProductImage(
        product_id=product_id,
        image_url=public_url,
        storage_key=req.storage_key,
        alt_text=req.alt_text,
        sort_order=next_order,
        is_primary=is_primary,
        file_size_bytes=req.file_size_bytes,
        mime_type=req.mime_type,
        width=req.width,
        height=req.height,
    )
    db.add(image)
    await db.flush()

    # Record audit log
    await log_audit_event(
        db,
        action="product_image.uploaded",
        entity_type="product_image",
        entity_id=str(image.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={
            "product_id": product_id,
            "storage_key": image.storage_key,
            "is_primary": image.is_primary,
        },
    )
    await db.flush()

    return image


async def reorder_product_images(
    db: AsyncSession,
    product_id: int,
    image_ids: List[int],
    actor_user: User,
) -> List[ProductImage]:
    """Update display sequence for product images."""
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    for idx, img_id in enumerate(image_ids):
        await db.execute(
            update(ProductImage)
            .where(ProductImage.id == img_id, ProductImage.product_id == product_id)
            .values(sort_order=idx)
        )

    await db.flush()

    # Record audit log
    await log_audit_event(
        db,
        action="product_images.reordered",
        entity_type="product",
        entity_id=str(product_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"reordered_image_ids": image_ids},
    )
    await db.flush()

    # Return ordered images
    result = await db.execute(
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order.asc())
    )
    return list(result.scalars().all())


async def set_primary_product_image(
    db: AsyncSession,
    product_id: int,
    image_id: int,
    actor_user: User,
) -> ProductImage:
    """Designate an image as the primary catalogue card thumbnail."""
    image = await db.get(ProductImage, image_id)
    if not image or image.product_id != product_id:
        raise AppException(
            message=f"Product image ID {image_id} not found for product {product_id}.",
            code="IMAGE_NOT_FOUND",
            status_code=404,
        )

    # Clear other primaries for this product
    await db.execute(
        update(ProductImage)
        .where(ProductImage.product_id == product_id)
        .values(is_primary=False)
    )

    image.is_primary = True
    await db.flush()

    # Audit log
    await log_audit_event(
        db,
        action="product_image.set_primary",
        entity_type="product_image",
        entity_id=str(image.id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"product_id": product_id, "image_id": image_id},
    )
    await db.flush()

    return image


async def delete_product_image(
    db: AsyncSession,
    product_id: int,
    image_id: int,
    actor_user: User,
) -> None:
    """Delete image database metadata and cleanup storage object from S3."""
    settings = get_settings()
    image = await db.get(ProductImage, image_id)
    if not image or image.product_id != product_id:
        raise AppException(
            message=f"Product image ID {image_id} not found for product {product_id}.",
            code="IMAGE_NOT_FOUND",
            status_code=404,
        )

    # 1. Clean up from S3 storage if storage_key is present
    if image.storage_key:
        storage_service = get_storage_service(settings)
        storage_service.delete_file(image.storage_key)

    was_primary = image.is_primary

    # 2. Delete database record
    await db.delete(image)
    await db.flush()

    # 3. If primary was deleted, promote first remaining image
    if was_primary:
        remaining_res = await db.execute(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order.asc())
            .limit(1)
        )
        first_remaining = remaining_res.scalar_one_or_none()
        if first_remaining:
            first_remaining.is_primary = True
            await db.flush()

    # 4. Audit log
    await log_audit_event(
        db,
        action="product_image.deleted",
        entity_type="product_image",
        entity_id=str(image_id),
        user_id=actor_user.id,
        actor_email=actor_user.email,
        details={"product_id": product_id, "storage_key": image.storage_key},
    )
    await db.flush()


async def list_product_images(
    db: AsyncSession,
    product_id: int,
) -> List[ProductImage]:
    """Retrieve gallery imagery for a product ordered by sort sequence."""
    result = await db.execute(
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order.asc())
    )
    return list(result.scalars().all())


async def add_product_image_url(
    db: AsyncSession,
    product_id: int,
    image_url: str,
    alt_text: Optional[str] = None,
    is_primary: bool = False,
    actor_user: Optional[User] = None,
) -> ProductImage:
    """Register an image for a product via direct URL."""
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    count_res = await db.execute(
        select(func.count(ProductImage.id)).where(ProductImage.product_id == product_id)
    )
    existing_count = count_res.scalar() or 0

    should_be_primary = is_primary or (existing_count == 0)

    if should_be_primary:
        await db.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_primary=False)
        )

    max_order_res = await db.execute(
        select(func.max(ProductImage.sort_order)).where(ProductImage.product_id == product_id)
    )
    max_order = max_order_res.scalar()
    next_order = (max_order + 1) if max_order is not None else 0

    image = ProductImage(
        product_id=product_id,
        image_url=image_url.strip(),
        storage_key=None,
        alt_text=alt_text or product.name,
        sort_order=next_order,
        is_primary=should_be_primary,
    )
    db.add(image)
    await db.flush()

    if actor_user:
        await log_audit_event(
            db,
            action="product_image.added_url",
            entity_type="product_image",
            entity_id=str(image.id),
            user_id=actor_user.id,
            actor_email=actor_user.email,
            details={"product_id": product_id, "image_url": image.image_url},
        )
        await db.flush()

    return image


async def upload_product_image_file(
    db: AsyncSession,
    product_id: int,
    file_bytes: bytes,
    original_filename: str,
    mime_type: str,
    alt_text: Optional[str] = None,
    is_primary: bool = False,
    actor_user: Optional[User] = None,
) -> ProductImage:
    """Save an uploaded product image file to disk and register in database."""
    product = await db.get(Product, product_id)
    if not product:
        raise AppException(
            message=f"Product with ID {product_id} not found.",
            code="PRODUCT_NOT_FOUND",
            status_code=404,
        )

    clean_filename = sanitize_filename(original_filename)
    unique_token = uuid.uuid4().hex[:10]
    filename = f"{product_id}_{unique_token}_{clean_filename}"

    uploads_dir = Path("/app/uploads") if os.path.exists("/app") else Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / filename

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    relative_url = f"/uploads/{filename}"
    image_url = f"http://localhost:8000{relative_url}"

    count_res = await db.execute(
        select(func.count(ProductImage.id)).where(ProductImage.product_id == product_id)
    )
    existing_count = count_res.scalar() or 0

    should_be_primary = is_primary or (existing_count == 0)

    if should_be_primary:
        await db.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_primary=False)
        )

    max_order_res = await db.execute(
        select(func.max(ProductImage.sort_order)).where(ProductImage.product_id == product_id)
    )
    max_order = max_order_res.scalar()
    next_order = (max_order + 1) if max_order is not None else 0

    image = ProductImage(
        product_id=product_id,
        image_url=image_url,
        storage_key=f"uploads/{filename}",
        alt_text=alt_text or product.name,
        sort_order=next_order,
        is_primary=should_be_primary,
        file_size_bytes=len(file_bytes),
        mime_type=mime_type,
    )
    db.add(image)
    await db.flush()

    if actor_user:
        await log_audit_event(
            db,
            action="product_image.uploaded_direct",
            entity_type="product_image",
            entity_id=str(image.id),
            user_id=actor_user.id,
            actor_email=actor_user.email,
            details={"product_id": product_id, "image_url": image.image_url},
        )
        await db.flush()

    return image
