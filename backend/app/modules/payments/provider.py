"""
Payment Provider Interface and Adapter Foundation (Module M14)
Defines provider-independent contracts for payment initiation, cryptographic webhook
signature verification, normalized callback parsing, direct status inquiry, and refunds.
Adheres strictly to the architectural mandate that online gateways require verified merchant
credentials and cannot assume availability in Pakistan without explicit configuration.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import json
from typing import Dict, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.modules.orders.models import Order
from app.modules.payments.models import Payment, Refund


class PaymentInitiationResult(BaseModel):
    """Normalized output from gateway payment checkout initialization."""
    provider_code: str
    provider_reference: str
    redirect_url: Optional[str] = None
    client_token: Optional[str] = None
    status: str = "pending"
    expires_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)


class PaymentVerificationResult(BaseModel):
    """Normalized output from direct server-to-server transaction status inquiry."""
    provider_code: str
    provider_reference: str
    order_reference: Optional[str] = None
    amount: Decimal
    currency_code: str = "PKR"
    status: str  # "paid", "failed", "pending", "cancelled"
    is_successful: bool
    raw_status: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class WebhookEventPayload(BaseModel):
    """Normalized payload parsed from provider webhook callback."""
    provider_code: str
    provider_event_id: Optional[str] = None
    event_type: str  # e.g. "payment.succeeded", "payment.failed", "refund.succeeded"
    provider_reference: Optional[str] = None
    order_reference: Optional[str] = None
    amount: Optional[Decimal] = None
    currency_code: str = "PKR"
    status: str  # "paid", "failed", "pending", "refunded"
    signature_verified: bool = False
    raw_payload: dict = Field(default_factory=dict)


class RefundResult(BaseModel):
    """Normalized output from gateway refund execution."""
    provider_code: str
    provider_reference: Optional[str] = None
    status: str  # "completed", "pending", "failed"
    amount: Decimal
    currency_code: str = "PKR"
    processed_at: datetime
    error_message: Optional[str] = None


class BasePaymentProvider(ABC):
    """
    Abstract Payment Provider Adapter.
    Decouples core checkout and order processing from specific third-party payment gateway APIs.
    """

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique provider code identifier."""
        pass

    @abstractmethod
    async def initiate_payment(
        self,
        order: Order,
        payment: Payment,
        return_url: str,
        cancel_url: str,
    ) -> PaymentInitiationResult:
        """Initialize payment with provider and obtain redirect URL or client-side checkout session."""
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
    ) -> bool:
        """Cryptographically verify authenticity of incoming provider callback signature."""
        pass

    @abstractmethod
    def parse_webhook_event(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
    ) -> WebhookEventPayload:
        """Parse raw HTTP callback payload into normalized WebhookEventPayload."""
        pass

    @abstractmethod
    async def verify_payment_status(
        self,
        provider_reference: str,
    ) -> PaymentVerificationResult:
        """Query provider directly to verify live status of a transaction."""
        pass

    @abstractmethod
    async def process_refund(
        self,
        payment: Payment,
        refund: Refund,
        reason: str,
    ) -> RefundResult:
        """Execute refund request with provider."""
        pass


class CodPaymentProvider(BasePaymentProvider):
    """Cash on Delivery provider adapter."""

    @property
    def provider_code(self) -> str:
        return "cod"

    async def initiate_payment(
        self,
        order: Order,
        payment: Payment,
        return_url: str,
        cancel_url: str,
    ) -> PaymentInitiationResult:
        return PaymentInitiationResult(
            provider_code="cod",
            provider_reference=order.order_number,
            status="pending",
            redirect_url=return_url,
            metadata={"payment_method": "cod", "notes": "Cash on Delivery payment"},
        )

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        return False

    def parse_webhook_event(self, headers: Dict[str, str], raw_body: bytes) -> WebhookEventPayload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cash on Delivery does not support automated webhook callbacks",
        )

    async def verify_payment_status(self, provider_reference: str) -> PaymentVerificationResult:
        return PaymentVerificationResult(
            provider_code="cod",
            provider_reference=provider_reference,
            amount=Decimal("0.00"),
            currency_code="PKR",
            status="pending",
            is_successful=False,
            raw_status="cod_pending",
        )

    async def process_refund(
        self,
        payment: Payment,
        refund: Refund,
        reason: str,
    ) -> RefundResult:
        return RefundResult(
            provider_code="cod",
            provider_reference=f"COD-RFD-{refund.refund_number}",
            status="completed",
            amount=refund.amount,
            currency_code=refund.currency_code,
            processed_at=datetime.now(timezone.utc),
        )


class MockOnlinePaymentProvider(BasePaymentProvider):
    """
    Test harness adapter for automated integration tests and local development.
    Validates HMAC-SHA256 signatures, produces realistic callbacks, and guarantees 100% contract compliance.
    """

    def __init__(self, webhook_secret: Optional[str] = None):
        settings = get_settings()
        if settings.APP_ENV == "test":
            self._secret = "mock-test-webhook-secret-key-32chars"
        else:
            self._secret = webhook_secret or "mock-test-webhook-secret-key-32chars"

    @property
    def provider_code(self) -> str:
        return "mock"

    async def initiate_payment(
        self,
        order: Order,
        payment: Payment,
        return_url: str,
        cancel_url: str,
    ) -> PaymentInitiationResult:
        ref = f"MOCK-TXN-{payment.id}-{int(datetime.now(timezone.utc).timestamp())}"
        redirect_url = f"https://sandbox.payment-gateway.test/checkout/{ref}?return={return_url}"
        return PaymentInitiationResult(
            provider_code="mock",
            provider_reference=ref,
            redirect_url=redirect_url,
            client_token=f"tok_mock_{payment.id}",
            status="pending",
            metadata={"order_number": order.order_number, "amount": str(payment.amount)},
        )

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        # Check header x-signature, x-provider-signature, or x-webhook-signature (case-insensitive)
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        received_sig = (
            normalized_headers.get("x-signature")
            or normalized_headers.get("x-provider-signature")
            or normalized_headers.get("x-webhook-signature")
        )
        if not received_sig:
            return False

        computed_sig = hmac.new(
            self._secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(received_sig, computed_sig)

    def parse_webhook_event(self, headers: Dict[str, str], raw_body: bytes) -> WebhookEventPayload:
        sig_ok = self.verify_webhook_signature(headers, raw_body)
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MALFORMED_WEBHOOK_PAYLOAD: Failed to parse JSON: {exc}",
            )

        event_id = data.get("event_id") or data.get("id")
        event_type = data.get("event_type") or data.get("type", "unknown")
        provider_ref = data.get("provider_reference") or data.get("transaction_id") or data.get("payment_reference")
        order_ref = data.get("order_number") or data.get("reference")
        amount_val = data.get("amount")
        amount = Decimal(str(amount_val)) if amount_val is not None else None
        currency = data.get("currency", "PKR")

        status_map = {
            "payment.succeeded": "paid",
            "payment.failed": "failed",
            "refund.succeeded": "refunded",
        }
        normalized_status = status_map.get(event_type, "pending")

        return WebhookEventPayload(
            provider_code="mock",
            provider_event_id=str(event_id) if event_id else None,
            event_type=event_type,
            provider_reference=str(provider_ref) if provider_ref else None,
            order_reference=str(order_ref) if order_ref else None,
            amount=amount,
            currency_code=currency,
            status=normalized_status,
            signature_verified=sig_ok,
            raw_payload=data,
        )

    async def verify_payment_status(self, provider_reference: str) -> PaymentVerificationResult:
        return PaymentVerificationResult(
            provider_code="mock",
            provider_reference=provider_reference,
            amount=Decimal("0.00"),
            currency_code="PKR",
            status="paid",
            is_successful=True,
            raw_status="settled",
        )

    async def process_refund(
        self,
        payment: Payment,
        refund: Refund,
        reason: str,
    ) -> RefundResult:
        ref = f"MOCK-RFD-{refund.refund_number}"
        return RefundResult(
            provider_code="mock",
            provider_reference=ref,
            status="completed",
            amount=refund.amount,
            currency_code=refund.currency_code,
            processed_at=datetime.now(timezone.utc),
        )


class UnconfiguredPaymentProvider(BasePaymentProvider):
    """
    Default online provider adapter when no payment gateway credentials have been verified.
    Explicitly refuses to simulate payment success to ensure complete financial integrity.
    """

    def __init__(self, requested_provider: str = "none"):
        self._provider = requested_provider

    @property
    def provider_code(self) -> str:
        return self._provider

    async def initiate_payment(
        self,
        order: Order,
        payment: Payment,
        return_url: str,
        cancel_url: str,
    ) -> PaymentInitiationResult:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"ONLINE_PAYMENT_NOT_CONFIGURED: Online payment provider '{self._provider}' is not yet configured with "
                "live merchant credentials for Pakistan. Please select Cash on Delivery or contact store support."
            ),
        )

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        return False

    def parse_webhook_event(self, headers: Dict[str, str], raw_body: bytes) -> WebhookEventPayload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ONLINE_PAYMENT_NOT_CONFIGURED: Gateway '{self._provider}' is unconfigured",
        )

    async def verify_payment_status(self, provider_reference: str) -> PaymentVerificationResult:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ONLINE_PAYMENT_NOT_CONFIGURED: Gateway '{self._provider}' is unconfigured",
        )

    async def process_refund(
        self,
        payment: Payment,
        refund: Refund,
        reason: str,
    ) -> RefundResult:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ONLINE_PAYMENT_NOT_CONFIGURED: Cannot process online refund through unconfigured provider '{self._provider}'",
        )


def get_payment_provider(provider_code: Optional[str] = None) -> BasePaymentProvider:
    """
    Factory resolving active payment provider adapter.
    If unconfigured or unknown, returns UnconfiguredPaymentProvider enforcing strict security.
    """
    settings = get_settings()
    target_code = (provider_code or settings.ONLINE_PAYMENT_PROVIDER).strip().lower()

    if target_code == "cod":
        return CodPaymentProvider()

    if target_code == "mock":
        return MockOnlinePaymentProvider(webhook_secret=settings.PAYMENT_WEBHOOK_SECRET)

    return UnconfiguredPaymentProvider(requested_provider=target_code)
