"""
Application Configuration Module
Reads configuration from environment variables and .env files using Pydantic Settings.
"""

from functools import lru_cache
from typing import List, Optional, Set, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VALID_ENVIRONMENTS: Set[str] = {"development", "test", "staging", "production"}
PROTECTED_ENVIRONMENTS: Set[str] = {"staging", "production"}


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "UniNova API"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = Field(
        ...,
        description="Application environment: development, test, staging, production",
    )
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api/v1"

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("APP_ENV must not be empty.")
        v_clean = v.strip()
        if v_clean not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid APP_ENV '{v}'. Must be one of: {', '.join(sorted(VALID_ENVIRONMENTS))}."
            )
        return v_clean

    # Security
    SECRET_KEY: str = Field(
        default="uninova-dev-insecure-secret-key-32-chars-minimum-needed",
        description="Secret key for signing sessions and cryptographic tokens",
    )

    # CORS Allowlist
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins as a list or comma-separated string",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # MySQL Database Settings
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "uninova_db"
    MYSQL_USER: str = "uninova_user"
    MYSQL_PASSWORD: str = "uninova_secure_password"

    # Database URLs (Explicit or computed)
    DATABASE_URL: Optional[str] = None
    DATABASE_URL_ASYNC: Optional[str] = None
    TEST_DATABASE_URL: Optional[str] = None

    @property
    def sync_database_url(self) -> str:
        """Return synchronous database connection string for Alembic migrations and admin tasks."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def async_database_url(self) -> str:
        """Return asynchronous database connection string for FastAPI runtime."""
        if self.DATABASE_URL_ASYNC:
            return self.DATABASE_URL_ASYNC
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    # Connection Pool Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # Recycle idle connections every 30 minutes
    DB_POOL_PRE_PING: bool = True  # Validate connection health before use

    # Commerce Settings (Pakistan Context)
    STORE_CURRENCY: str = "PKR"
    FREE_SHIPPING_THRESHOLD: int = 5000
    STANDARD_SHIPPING_FEE: int = 350
    COD_ENABLED: bool = True

    # Online Payment Gateway Settings (Pakistan Context)
    ONLINE_PAYMENT_PROVIDER: str = "none"  # Options: none, mock, safepay, payfast, jazzcash, easypaisa
    PAYMENT_WEBHOOK_SECRET: Optional[str] = None
    PAYMENT_GATEWAY_API_KEY: Optional[str] = None
    PAYMENT_GATEWAY_MERCHANT_ID: Optional[str] = None
    PAYMENT_GATEWAY_BASE_URL: Optional[str] = None

    # Media & AWS S3 / CloudFront Storage
    STORAGE_BACKEND: str = "mock"  # Options: mock, local, s3
    AWS_REGION: str = "ap-southeast-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET_NAME: str = "uninova-media"
    AWS_CLOUDFRONT_DOMAIN: Optional[str] = None
    MEDIA_UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB maximum image size
    MEDIA_ALLOWED_MIME_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/avif",
    ]
    PRESIGNED_URL_EXPIRE_SECONDS: int = 900  # 15 minutes

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.APP_ENV in PROTECTED_ENVIRONMENTS:
            if (
                self.SECRET_KEY == "uninova-dev-insecure-secret-key-32-chars-minimum-needed"
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError(
                    f"In {self.APP_ENV} (APP_ENV={self.APP_ENV}), SECRET_KEY must be a cryptographically secure random string of at least 32 characters."
                )
            if self.MYSQL_PASSWORD == "uninova_secure_password":
                raise ValueError(
                    f"In {self.APP_ENV} (APP_ENV={self.APP_ENV}), MYSQL_PASSWORD must not be the default development password."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached instance of application settings."""
    return Settings()
