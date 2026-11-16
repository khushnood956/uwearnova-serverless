"""
Storage Abstraction and Adapters
Supports AWS S3 direct upload via presigned URLs, CloudFront CDN URL resolution,
and mock/local implementations for isolated testing.
"""

from abc import ABC, abstractmethod
import re
from typing import Any, Dict, Optional
import boto3
from botocore.config import Config

from app.core.config import Settings, get_settings


class BaseStorageService(ABC):
    """Abstract storage interface ensuring application logic is independent of cloud provider."""

    @abstractmethod
    def generate_presigned_upload(
        self,
        storage_key: str,
        mime_type: str,
        max_bytes: int,
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """Generate a short-lived presigned URL allowing client to PUT object directly to storage."""
        pass

    @abstractmethod
    def get_public_url(self, storage_key: str) -> str:
        """Resolve public CDN or bucket URL for a storage key."""
        pass

    @abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Delete object from storage."""
        pass

    @abstractmethod
    def file_exists(self, storage_key: str) -> bool:
        """Verify whether an object exists in storage."""
        pass


class S3StorageService(BaseStorageService):
    """Production AWS S3 adapter with optional CloudFront CDN URL resolution."""

    def __init__(self, settings: Settings):
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self.cloudfront_domain = settings.AWS_CLOUDFRONT_DOMAIN

        boto_config = Config(
            signature_version="s3v4",
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "standard"},
        )

        client_kwargs: Dict[str, Any] = {
            "service_name": "s3",
            "region_name": self.region,
            "config": boto_config,
        }
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        self.s3_client = boto3.client(**client_kwargs)

    def generate_presigned_upload(
        self,
        storage_key: str,
        mime_type: str,
        max_bytes: int,
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """Generate a presigned PUT URL with Content-Type constraint."""
        upload_url = self.s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": storage_key,
                "ContentType": mime_type,
            },
            ExpiresIn=expires_in,
        )

        return {
            "upload_url": upload_url,
            "http_method": "PUT",
            "required_headers": {"Content-Type": mime_type},
            "storage_key": storage_key,
            "public_url": self.get_public_url(storage_key),
            "expires_in_seconds": expires_in,
        }

    def get_public_url(self, storage_key: str) -> str:
        """Return CloudFront CDN URL if configured, otherwise standard S3 virtual-hosted URL."""
        clean_key = storage_key.lstrip("/")
        if self.cloudfront_domain:
            domain = self.cloudfront_domain.strip("/")
            # If domain does not include scheme, prepend https://
            if not domain.startswith("http://") and not domain.startswith("https://"):
                domain = f"https://{domain}"
            return f"{domain}/{clean_key}"

        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{clean_key}"

    def delete_file(self, storage_key: str) -> bool:
        """Remove file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except Exception:
            return False

    def file_exists(self, storage_key: str) -> bool:
        """Verify object existence via HeadObject."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except Exception:
            return False


class MockStorageService(BaseStorageService):
    """
    Mock storage adapter used for testing and offline local development.
    Avoids network calls or live AWS credential requirements.
    """

    def __init__(self, settings: Settings):
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.cloudfront_domain = settings.AWS_CLOUDFRONT_DOMAIN or "media.uninova.example.com"
        self.stored_files: set[str] = set()
        self.deleted_files: set[str] = set()

    def generate_presigned_upload(
        self,
        storage_key: str,
        mime_type: str,
        max_bytes: int,
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """Generate a deterministic simulated presigned upload URL."""
        self.stored_files.add(storage_key)
        return {
            "upload_url": f"https://mock-s3.uninova.local/{self.bucket_name}/{storage_key}?signed=true",
            "http_method": "PUT",
            "required_headers": {"Content-Type": mime_type},
            "storage_key": storage_key,
            "public_url": self.get_public_url(storage_key),
            "expires_in_seconds": expires_in,
        }

    def get_public_url(self, storage_key: str) -> str:
        """Return simulated CDN URL."""
        clean_key = storage_key.lstrip("/")
        domain = self.cloudfront_domain.strip("/")
        if not domain.startswith("http://") and not domain.startswith("https://"):
            domain = f"https://{domain}"
        return f"{domain}/{clean_key}"

    def delete_file(self, storage_key: str) -> bool:
        """Track file deletion in mock state."""
        self.stored_files.discard(storage_key)
        self.deleted_files.add(storage_key)
        return True

    def file_exists(self, storage_key: str) -> bool:
        """Check if file exists in mock state."""
        return storage_key in self.stored_files


def get_storage_service(settings: Optional[Settings] = None) -> BaseStorageService:
    """Factory returning configured storage adapter instance."""
    active_settings = settings or get_settings()
    if active_settings.STORAGE_BACKEND == "s3":
        return S3StorageService(active_settings)
    return MockStorageService(active_settings)


def sanitize_filename(filename: str) -> str:
    """Normalize file name, removing non-alphanumeric chars for secure S3 object keys."""
    # Replace whitespace and invalid characters with hyphens
    sanitized = re.sub(r"[^\w\.-]", "-", filename.lower())
    # Collapse multiple hyphens
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized.strip("-")
