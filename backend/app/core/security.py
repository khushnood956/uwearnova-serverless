"""
Security & Cryptography Module
Implements Argon2id password hashing and PyJWT token generation/verification.
Follows OWASP authentication guidelines and docs/backend/01-backend-architecture.md.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from app.core.config import get_settings

settings = get_settings()

# Argon2id password hasher (OWASP recommended parameters)
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a raw token for safe database persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_token(nbytes: int = 36) -> str:
    """Generate high-entropy cryptographic random string."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(
    user_id: int,
    user_type: str = "customer",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create short-lived JWT access token containing user identity and type claims."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=30)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "user_type": user_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Returns token payload dict on success, None if expired or invalid signature.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None
