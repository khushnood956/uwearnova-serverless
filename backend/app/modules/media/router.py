"""
Product Media API Endpoints
Presigned S3 upload intent, direct upload confirmation, image reordering,
primary thumbnail management, and S3 file deletion.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.catalog.schemas import (
    AddImageUrlRequest,
    ConfirmUploadRequest,
    PresignedUploadRequest,
    PresignedUploadResponse,
    ProductImageResponse,
    ReorderImagesRequest,
)
from app.modules.media.service import (
    add_product_image_url,
    confirm_product_image_upload,
    delete_product_image,
    list_product_images,
    reorder_product_images,
    request_product_image_upload,
    set_primary_product_image,
    upload_product_image_file,
)
from app.modules.rbac.dependencies import require_permission

admin_media_router = APIRouter(
    prefix="/admin/products/{product_id}/media",
    tags=["Admin: Product Media & S3"],
)


@admin_media_router.post(
    "/upload-intent",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Request Presigned S3 Upload URL",
)
async def request_upload_intent(
    product_id: int,
    req: PresignedUploadRequest,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> PresignedUploadResponse:
    """Validate file metadata and issue a short-lived presigned PUT URL for direct client S3 upload."""
    return await request_product_image_upload(
        db,
        product_id=product_id,
        req=req,
        actor_user=current_user,
    )


@admin_media_router.post(
    "/confirm",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Confirm Upload & Register Image Metadata",
)
async def confirm_upload(
    product_id: int,
    req: ConfirmUploadRequest,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> ProductImageResponse:
    """Register uploaded S3 object in MySQL with sort order and primary thumbnail exclusivity."""
    image = await confirm_product_image_upload(
        db,
        product_id=product_id,
        req=req,
        actor_user=current_user,
    )
    return ProductImageResponse.model_validate(image)


@admin_media_router.get(
    "",
    response_model=List[ProductImageResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: List Product Images",
)
async def get_media(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("products.read")),
) -> List[ProductImageResponse]:
    """Retrieve gallery imagery and metadata for a product ordered by sequence."""
    images = await list_product_images(db, product_id=product_id)
    return [ProductImageResponse.model_validate(img) for img in images]


@admin_media_router.put(
    "/reorder",
    response_model=List[ProductImageResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: Reorder Product Images",
)
async def reorder_media(
    product_id: int,
    req: ReorderImagesRequest,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> List[ProductImageResponse]:
    """Update gallery display sequence for a product's imagery."""
    images = await reorder_product_images(
        db,
        product_id=product_id,
        image_ids=req.image_ids,
        actor_user=current_user,
    )
    return [ProductImageResponse.model_validate(img) for img in images]


@admin_media_router.put(
    "/{image_id}/set-primary",
    response_model=ProductImageResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Designate Primary Image",
)
async def set_primary_image(
    product_id: int,
    image_id: int,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> ProductImageResponse:
    """Set an image as the primary storefront thumbnail, unsetting all other images for this product."""
    image = await set_primary_product_image(
        db,
        product_id=product_id,
        image_id=image_id,
        actor_user=current_user,
    )
    return ProductImageResponse.model_validate(image)


@admin_media_router.delete(
    "/{image_id}",
    status_code=status.HTTP_200_OK,
    summary="Admin: Delete Product Image",
)
async def delete_image(
    product_id: int,
    image_id: int,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
):
    """Delete image metadata from database and delete underlying file from S3."""
    await delete_product_image(
        db,
        product_id=product_id,
        image_id=image_id,
        actor_user=current_user,
    )
    return {"message": f"Product image {image_id} successfully deleted."}


@admin_media_router.post(
    "/add-url",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Add Image via Direct URL",
)
async def add_image_url(
    product_id: int,
    req: AddImageUrlRequest,
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> ProductImageResponse:
    """Attach an image to the product using a direct public URL."""
    image = await add_product_image_url(
        db,
        product_id=product_id,
        image_url=req.image_url,
        alt_text=req.alt_text,
        is_primary=req.is_primary,
        actor_user=current_user,
    )
    return ProductImageResponse.model_validate(image)


@admin_media_router.post(
    "/upload",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Upload Image File Directly",
)
async def upload_image(
    product_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    current_user: User = Depends(require_permission("products.update")),
    db: AsyncSession = Depends(get_db),
) -> ProductImageResponse:
    """Upload a product image file directly to server storage."""
    contents = await file.read()
    image = await upload_product_image_file(
        db,
        product_id=product_id,
        file_bytes=contents,
        original_filename=file.filename or "image.jpg",
        mime_type=file.content_type or "image/jpeg",
        alt_text=alt_text,
        is_primary=is_primary,
        actor_user=current_user,
    )
    return ProductImageResponse.model_validate(image)
