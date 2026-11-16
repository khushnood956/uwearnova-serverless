# Payment Provider Integration Guide & Pakistan Gateway Architecture

This guide documents the payment provider architecture for the platform, detailing how to integrate external online payment gateways, handle asynchronous webhooks, manage idempotency and refunds, and comply with Pakistan's digital commerce regulatory framework.

---

## 1. Executive Summary & Anti-Assumption Notice

> **Critical Rule:** In compliance with project guidelines, **never assume an online payment provider is active without valid production credentials and sandbox verification.**
> The system defaults to `ONLINE_PAYMENT_PROVIDER=none`, which attaches the `UnconfiguredPaymentProvider`. Any attempt by customers to initiate online payments when unconfigured will fail with HTTP 400 (`ONLINE_PAYMENT_NOT_CONFIGURED`). Fake successful payments or mock gateways must never run in production environments.

---

## 2. Digital Payments Landscape in Pakistan

The Pakistani payment ecosystem operates under State Bank of Pakistan (SBP) Payment System Operators (PSO) and Payment Service Providers (PSP) regulatory frameworks. Digital e-commerce merchants primarily interface with one or more of the following gateway categories:

| Gateway / Provider | Type & Rail | Common Use Case | SBP Status & Onboarding |
| :--- | :--- | :--- | :--- |
| **Safepay** | Modern Developer-First PSP / Card & Wallet Aggregator | Visa / Mastercard, PayPak, EasyPaisa, JazzCash | SBP Licensed EMI/PSP. Sandbox and production API keys, HMAC-SHA256 webhooks. |
| **PayFast (APPS)** | SBP-Licensed PSO/PSP | Direct Bank Debit, Visa / Mastercard, UnionPay, 1LINK | Direct checkout redirect, merchant tokenization, server-to-server IPN. |
| **JazzCash (Mobilink Microfinance)** | Mobile Wallet & Card Aggregator | JazzCash Wallets, OTC (Voucher), Debit/Credit Cards | Merchant portal, secure redirect with hash calculation (HMAC-SHA256). |
| **EasyPaisa (Telenor Bank)** | Mobile Wallet & Gateway | EasyPaisa Wallets, MA (Mobile Account), OTC | Merchant API with store ID, hash authentication, IPN callbacks. |
| **Bank Direct Gateways (HBL Pay / UBL / MCB)** | Cybersource / MPGS White-label | High-volume card processing (Visa/Mastercard) | Requires SBP-compliant merchant account, 3D-Secure 2.0 (3DS2) compliance. |

### Key Regulatory & Operational Requirements in Pakistan
1. **3D Secure 2.0 (3DS2):** SBP mandates Two-Factor Authentication (2FA) / OTP for all domestic e-commerce card transactions. Direct server-to-server card processing without 3DS redirection is prohibited for domestic cards.
2. **Pakistani Rupee (PKR) Settlement:** All consumer pricing and merchant settlements must clear in PKR.
3. **FBR / Provincial Sales Tax Digital Invoicing:** Transaction IDs must be linked to immutable order items for auditing against provincial tax authorities (SRB, PRA, BRA, KPRA) and federal POS reporting where applicable.
4. **Dispute & Chargeback Windows:** Standard card disputes follow 120-day Visa/Mastercard cycles; wallet disputes generally require 7–14 day resolution windows.

---

## 3. Architecture Overview

The payment engine uses a provider-independent design decoupled from the core checkout and order state machines:

```
                  ┌──────────────────────┐
                  │    Checkout Service  │
                  └──────────┬───────────┘
                             │ creates Payment record (status: pending)
                             ▼
                  ┌──────────────────────┐
                  │   Payment Service    │
                  └──────────┬───────────┘
                             │ delegates to provider via Factory
                             ▼
                  ┌──────────────────────┐
                  │ BasePaymentProvider  │ ◄── (Abstract Interface)
                  └──────────┬───────────┘
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  CodPayment-    │ │  MockOnline-    │ │  Unconfigured-  │
│  Provider       │ │  Provider       │ │  Provider       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │
  In-person cash      HMAC Sandbox        Strict Rejection
  reconciliation      Testing Adapter     (Default Production)
```

### Core Abstractions (`backend/app/modules/payments/provider.py`)
- `BasePaymentProvider`: Abstract base class enforcing:
  - `initiate_payment(order, payment, return_url, cancel_url) -> PaymentInitiationResult`
  - `verify_payment(payment, reference) -> PaymentVerificationResult`
  - `parse_and_verify_webhook(headers, raw_body) -> WebhookEventPayload`
  - `process_refund(payment, refund, reason) -> RefundResult`
- `get_payment_provider(provider_code: str) -> BasePaymentProvider`: Dynamic factory resolving the configured provider.

---

## 4. Webhook Security & Idempotency Protocol

Webhooks arrive asynchronously from external gateways. To prevent fraud, double-crediting, and replay attacks, all webhooks pass through a 4-tier validation pipeline:

### 1. Cryptographic Signature Verification
Every incoming payload must be signed using HMAC-SHA256:
```
signature = HMAC-SHA256(key=PAYMENT_WEBHOOK_SECRET, message=raw_body)
```
- Missing or invalid signatures immediately abort with `401 Unauthorized`.
- Timestamp checks (if supplied by the provider) reject replays older than 300 seconds.

### 2. Event Log Persistence (`payment_events` table)
Before processing business logic, every webhook attempt is logged:
- `provider_code`: e.g., `safepay`, `payfast`, `mock`
- `provider_event_id`: Gateway transaction ID or notification GUID
- `signature_verified`: Boolean audit trail
- `payload`: Exact JSON/string payload received
- `processing_status`: `pending` -> `processed` / `failed` / `ignored`

### 3. Idempotency Check
If `(provider_code, provider_event_id)` has already been recorded with `processing_status="processed"`, the endpoint immediately returns HTTP 200 with `{"status": "already_processed"}` without executing order updates or balance mutations.

### 4. Atomic Database Transitions
- Transaction status is updated inside a single database transaction.
- An immutable `PaymentTransaction` record is created (type: `charge` or `refund`).
- The parent `Order` status transitions from `unpaid` to `paid` if `amount_collected >= order.total_amount`.

---

## 5. Step-by-Step: Adding a New Payment Gateway (e.g. Safepay)

To integrate a new gateway, follow these steps:

### Step 1: Update Environment Configuration
In `backend/app/core/config.py`:
```python
ONLINE_PAYMENT_PROVIDER: str = "safepay"  # or payfast, jazzcash, none
PAYMENT_WEBHOOK_SECRET: str = "prod_webhook_secret_..."
PAYMENT_GATEWAY_API_KEY: str = "sec_..."
PAYMENT_GATEWAY_MERCHANT_ID: str = "merchant_..."
PAYMENT_GATEWAY_BASE_URL: str = "https://api.getsafepay.com"
```

### Step 2: Implement `BasePaymentProvider`
Create a new file `backend/app/modules/payments/providers/safepay.py`:
```python
import hmac
import hashlib
import json
import httpx
from backend.app.modules.payments.provider import (
    BasePaymentProvider,
    PaymentInitiationResult,
    PaymentVerificationResult,
    WebhookEventPayload,
    RefundResult,
)

class SafepayPaymentProvider(BasePaymentProvider):
    def __init__(self, api_key: str, secret: str, base_url: str):
        self.api_key = api_key
        self.secret = secret
        self.base_url = base_url

    async def initiate_payment(self, order, payment, return_url, cancel_url):
        # 1. Call Safepay /order/v1/init endpoint
        # 2. Return redirect URL to Safepay checkout tracker
        return PaymentInitiationResult(
            provider_code="safepay",
            provider_transaction_id="safepay_tracker_token",
            redirect_url="https://getsafepay.com/checkout/pay?beacon=...",
            client_token="...",
            metadata={"order_id": order.id}
        )

    def parse_and_verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> WebhookEventPayload:
        signature = headers.get("x-sfpy-signature", "")
        expected = hmac.new(self.secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid Safepay signature")
        
        data = json.loads(raw_body)
        return WebhookEventPayload(
            event_id=data["notification_id"],
            event_type=data["type"],  # e.g., 'payment.completed'
            payment_reference=data["data"]["tracker"]["token"],
            amount=Decimal(str(data["data"]["amount"])),
            currency="PKR",
            raw_payload=data,
            signature_valid=True
        )
```

### Step 3: Register in the Provider Factory
In `backend/app/modules/payments/provider.py`:
```python
if provider_code == "safepay":
    return SafepayPaymentProvider(
        api_key=settings.PAYMENT_GATEWAY_API_KEY,
        secret=settings.PAYMENT_WEBHOOK_SECRET,
        base_url=settings.PAYMENT_GATEWAY_BASE_URL
    )
```

### Step 4: Configure Webhook Route in Gateway Portal
Point the gateway webhook setting to:
```
POST https://api.yourdomain.com/api/v1/payments/webhooks/safepay
```

---

## 6. Refund Lifecycle

Refunds are initiated by authorized staff (`admin` or `customer_service` with `orders:refund` permissions):
1. **Validation:** Refund amount cannot exceed `payment.amount_collected - sum(previous_completed_refunds)`.
2. **Provider Call:** Dispatches `provider.process_refund()`.
3. **Ledger Record:** Creates a `Refund` record with unique identifier (`REF-YYYYMMDD-XXXXXX`) and status `completed` or `pending`.
4. **Payment Update:** Subtracts from `amount_collected` or adjusts `outstanding_amount`. Creates an audit `PaymentTransaction` with `type="refund"`.

---

## 7. Sandbox Testing Checklist

Before deploying any online gateway integration to production:
- [ ] Merchant account fully verified with SBP-regulated acquirer/bank.
- [ ] Webhook URL registered with valid SSL/TLS certificate.
- [ ] Webhook secret configured and HMAC verification tested with tampered and valid bodies.
- [ ] Out-of-order webhook delivery tested (e.g., webhook arrives before user redirect completes).
- [ ] Duplicate webhook delivery tested (idempotency verified).
- [ ] Partial and full refund flows verified.
- [ ] Failed payment and cancelled checkout redirection verified.
- [ ] Logging verified to ensure no sensitive card data (PAN, CVV, PIN) is ever logged.
