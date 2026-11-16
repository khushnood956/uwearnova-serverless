"""
Authentication & Identity API Endpoints
Provides customer registration, login, token rotation, logout, and password recovery.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import (
    authenticate_user,
    change_password,
    create_password_reset_token,
    create_user_tokens,
    register_user,
    reset_password_with_token,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Customer",
)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await register_user(db, req)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate User & Issue Tokens",
)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await authenticate_user(db, email=req.email, password=req.password)
    return await create_user_tokens(db, user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate Refresh Token",
)
async def refresh_token_endpoint(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await rotate_refresh_token(db, raw_refresh_token=req.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Refresh Token (Logout)",
)
async def logout(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await revoke_refresh_token(db, raw_refresh_token=req.refresh_token)
    return MessageResponse(message="Successfully logged out and session revoked.")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Authenticated User",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Password",
)
async def update_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await change_password(
        db,
        user=current_user,
        current_password=req.current_password,
        new_password=req.new_password,
    )
    return MessageResponse(message="Password successfully updated. Other active sessions have been revoked.")


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Password Reset",
)
async def request_password_reset(
    req: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    # Generates reset token (in production sent via email/SMS; returns generic message)
    await create_password_reset_token(db, email=req.email)
    return MessageResponse(
        message="If an account with that email exists, password reset instructions have been dispatched."
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm Password Reset with Token",
)
async def confirm_password_reset(
    req: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await reset_password_with_token(db, raw_token=req.token, new_password=req.new_password)
    return MessageResponse(message="Password has been successfully reset. Please log in with your new credentials.")
