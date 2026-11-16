"""
Authentication & Identity Service Layer
Handles user registration, authentication, token rotation, revocation, and password recovery.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import AppException
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.models import PasswordReset, RefreshToken, User
from app.modules.auth.schemas import RegisterRequest, TokenResponse


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime object is timezone-aware in UTC across all database engines."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def register_user(db: AsyncSession, req: RegisterRequest) -> User:
    """Register a new customer account after checking email uniqueness."""
    query = select(User).where(User.email == req.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise AppException(
            message="An account with this email address already exists.",
            code="EMAIL_ALREADY_EXISTS",
            status_code=409,
        )

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        phone=req.phone,
        status="active",
        user_type="customer",
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """
    Authenticate user credentials with brute-force protection and lockout checks.
    """
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not user:
        # Generic error message to prevent user enumeration
        raise AppException(
            message="Invalid email or password.",
            code="INVALID_CREDENTIALS",
            status_code=401,
        )

    # Check account lockout
    locked_until = _ensure_utc(user.locked_until)
    if locked_until and locked_until > now:
        minutes_left = max(1, int((locked_until - now).total_seconds() / 60))
        raise AppException(
            message=f"Account temporarily locked due to too many failed attempts. Try again in {minutes_left} minutes.",
            code="ACCOUNT_LOCKED",
            status_code=423,
        )

    # Check account status
    if user.status != "active":
        raise AppException(
            message=f"Account is currently {user.status}. Please contact concierge.",
            code="ACCOUNT_INACTIVE",
            status_code=403,
        )

    # Verify password hash
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        # Commit failed attempt tracking to survive the 401 response
        await db.commit()
        raise AppException(
            message="Invalid email or password.",
            code="INVALID_CREDENTIALS",
            status_code=401,
        )

    # Successful login: reset attempts and record timestamp
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    await db.flush()
    return user


async def create_user_tokens(db: AsyncSession, user: User) -> TokenResponse:
    """Generate a JWT access token and persist a cryptographically secure refresh token."""
    access_token = create_access_token(user_id=user.id, user_type=user.user_type)
    raw_refresh_token = generate_secure_token(48)
    token_digest = hash_token(raw_refresh_token)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=14)

    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=token_digest,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(refresh_record)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        token_type="bearer",
        expires_in=1800,
    )


async def rotate_refresh_token(db: AsyncSession, raw_refresh_token: str) -> TokenResponse:
    """
    Validate and rotate refresh token. Revokes the presented token and issues a fresh pair.
    """
    token_digest = hash_token(raw_refresh_token)
    now = datetime.now(timezone.utc)

    query = select(RefreshToken).where(RefreshToken.token_hash == token_digest)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record or record.revoked:
        raise AppException(
            message="Invalid, expired, or revoked refresh token.",
            code="INVALID_REFRESH_TOKEN",
            status_code=401,
        )

    expires_at = _ensure_utc(record.expires_at)
    if expires_at and expires_at < now:
        raise AppException(
            message="Invalid, expired, or revoked refresh token.",
            code="INVALID_REFRESH_TOKEN",
            status_code=401,
        )

    # Revoke current refresh token
    record.revoked = True

    # Retrieve user
    user_query = select(User).where(User.id == record.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user or user.status != "active":
        raise AppException(
            message="User account associated with this token is not active.",
            code="USER_NOT_ACTIVE",
            status_code=401,
        )

    # Issue new token pair
    return await create_user_tokens(db, user)


async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> bool:
    """Revoke a single refresh token during logout."""
    token_digest = hash_token(raw_refresh_token)
    query = select(RefreshToken).where(RefreshToken.token_hash == token_digest)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if record:
        record.revoked = True
        await db.flush()
        return True
    return False


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Change user password after verifying current credentials and revoke existing sessions."""
    if not verify_password(current_password, user.password_hash):
        raise AppException(
            message="Current password is incorrect.",
            code="INVALID_PASSWORD",
            status_code=400,
        )

    user.password_hash = hash_password(new_password)

    # Revoke all active refresh tokens for security
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)
        .values(revoked=True)
    )
    await db.execute(stmt)
    await db.flush()


async def create_password_reset_token(db: AsyncSession, email: str) -> Optional[str]:
    """
    Generate and store a password reset token for the specified email.
    Returns raw token if user exists, None otherwise (prevents enumeration).
    """
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return None

    raw_token = generate_secure_token(32)
    token_digest = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)

    reset_record = PasswordReset(
        user_id=user.id,
        token_hash=token_digest,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_record)
    await db.flush()
    return raw_token


async def reset_password_with_token(
    db: AsyncSession,
    raw_token: str,
    new_password: str,
) -> None:
    """Redeem a valid password reset token and update the user's password."""
    token_digest = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    query = select(PasswordReset).where(
        PasswordReset.token_hash == token_digest,
        PasswordReset.used == False,
    )
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise AppException(
            message="Invalid or expired password reset token.",
            code="INVALID_RESET_TOKEN",
            status_code=400,
        )

    expires_at = _ensure_utc(record.expires_at)
    if expires_at and expires_at < now:
        raise AppException(
            message="Invalid or expired password reset token.",
            code="INVALID_RESET_TOKEN",
            status_code=400,
        )

    record.used = True

    # Retrieve user and update password
    user_query = select(User).where(User.id == record.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise AppException(
            message="Associated user account not found.",
            code="USER_NOT_FOUND",
            status_code=404,
        )

    user.password_hash = hash_password(new_password)

    # Invalidate existing sessions
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)
        .values(revoked=True)
    )
    await db.execute(stmt)
    await db.flush()
