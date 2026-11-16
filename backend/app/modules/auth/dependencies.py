"""
Authentication Dependencies
Extracts and validates current authenticated user from JWT Bearer tokens.
"""

from typing import Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import AppException
from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.auth.models import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate access token and return the active User entity.
    Raises 401 UNAUTHORIZED if missing, expired, or invalid.
    """
    if not token:
        raise AppException(
            message="Authentication credentials were not provided.",
            code="UNAUTHORIZED",
            status_code=401,
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AppException(
            message="Invalid or expired access token.",
            code="INVALID_TOKEN",
            status_code=401,
        )

    try:
        user_id = int(payload["sub"])
    except ValueError:
        raise AppException(
            message="Malformed token subject identifier.",
            code="INVALID_TOKEN",
            status_code=401,
        )

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AppException(
            message="User account no longer exists.",
            code="USER_NOT_FOUND",
            status_code=401,
        )

    if user.status != "active":
        raise AppException(
            message=f"User account is {user.status}.",
            code="ACCOUNT_INACTIVE",
            status_code=403,
        )

    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Retrieve authenticated user if valid token present, otherwise None for anonymous guests."""
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None

    query = select(User).where(User.id == user_id, User.status == "active")
    result = await db.execute(query)
    return result.scalar_one_or_none()
