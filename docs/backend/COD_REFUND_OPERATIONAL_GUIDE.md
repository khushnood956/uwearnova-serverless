# Cash on Delivery (COD) Refund Operational Standard Operating Procedure (SOP)

This document establishes the official operational and financial reconciliation procedure for issuing refunds on orders originally placed and collected via **Cash on Delivery (COD)** in Pakistan.

---

## 1. Regulatory Context & The Pakistan Logistics Reality

In Pakistan's retail e-commerce ecosystem:
1. **Courier Riders Never Carry or Reverse Cash:** Domestic courier delivery associates (TCS, Leopards, Trax, PostEx, Call Courier, M&P) are contracted strictly for **inward cash collection**. Courier riders are never authorized to disburse cash or reverse funds to customers at their doorstep upon collecting returned parcels.
2. **Anti-Fraud & State Bank of Pakistan (SBP) Compliance:** Automatic disbursement or unverified cash handovers represent severe financial leakage risks. SBP anti-money laundering (AML) and financial governance rules require verified audit trails with authenticated beneficiary identification.
3. **Mandatory Manual Operational Protocol:** Under platform architecture rules:
   > *"Do not automatically refund money without verified payment-provider support or an authorized manual process."*
   All COD refunds must follow the documented, staff-verified payout procedure below.

---

## 2. Permitted COD Refund Payout Rails

For returned COD orders that have successfully passed warehouse quality inspection, authorized finance staff may disburse funds via one of the following three rails:

| Payout Rail | Verification Requirements | SLA / Clearance | Use Case |
| :--- | :--- | :--- | :--- |
| **Direct Bank Transfer (1LINK / IBAN)** | Bank Name, Account Title, 24-digit PK IBAN | 1–2 Business Days | Preferred default for customer monetary refunds. |
| **Mobile Wallet (JazzCash / EasyPaisa)** | Registered Mobile Number, Account Holder Title | Immediate / Same Day | Fast payouts for mobile wallet users. |
| **Store Credit Voucher** | UniNova Customer Account ID | Instantaneous | Client opts for credit towards future garment purchases. |

---

## 3. Step-by-Step Operational Workflow

```
[1. Return Delivered to Warehouse]
              │
              ▼
[2. QC Garment Inspection] ──(Passed)──► [3. Stock Restocked in ERP]
              │
              ▼
[4. Finance Staff Verification: Verified COD Collection on Order]
              │
              ▼
[5. Beneficiary Account Verification (Title Match)]
              │
              ▼
[6. Electronic Payout via Banking Portal / 1LINK]
              │
              ▼
[7. Record Transaction ID & Execute Ledger Mutation in UniNova Admin]
              │
              ▼
[8. Return Status: 'completed' & Order State Updated]
```

### Step 1: Verification of Inward Remittance
Before issuing any COD refund, the finance operator must verify that:
- The order status was `delivered`.
- The payment record status was `paid` or `reconciled`.
- The courier remittance settlement batch voucher was logged and verified in the database.
- **Rule:** Unreconciled or unpaid COD orders cannot be refunded.

### Step 2: Quality Inspection Sign-Off
The warehouse quality inspector must sign off on the returned garment (`inspection_status="passed"`).
- Items marked `restock_available` are transactionally restored to available stock.
- Items marked `damaged` or `altered` are written off and ineligible for refund.

### Step 3: Beneficiary Verification
Customer Care contacts the customer to collect or verify beneficiary details:
- **Bank Transfers:** Customer provides official 24-digit IBAN (e.g., `PK36SCBL0000001123456701`) and Account Title. The account title must match the order recipient name or verified national identity.
- **Mobile Wallets:** Customer provides active JazzCash or EasyPaisa account number and title.

### Step 4: Electronic Payout & Ledger Entry
An authorized staff member with `refunds.create` permissions executes the transaction:
1. Disburses the approved PKR amount through corporate banking / 1LINK.
2. Navigates to `POST /api/v1/admin/returns/{return_id}/resolve-refund` in the UniNova API.
3. Submits:
   - `payout_method`: `"bank_transfer"` or `"wallet_transfer"`
   - `payout_reference`: Bank IMD/FT reference number (e.g., `FT2631509812`) or Wallet Transaction GUID.
   - `notes`: Documenting operator remarks and payout timestamp.
4. The system:
   - Generates an immutable `Refund` record (`RFD-YYYYMMDD-XXXXXX`).
   - Decrements `payment.amount_collected` and updates `payment.status` to `partially_refunded` or `refunded`.
   - Records an immutable `PaymentTransaction` with action `"refunded"`.
   - Closes the return request as `completed`.
   - Logs an audit event (`return.refund_processed`).

---

## 4. Anti-Fraud & Prevention Rules

1. **No Duplicate Refunds:** The platform validates that cumulative refunds never exceed verified collected funds.
2. **Rejection of Unreferenced Payouts:** Submitting a COD refund without a valid transaction reference (`payout_reference`) is strictly rejected by the API.
3. **Audit Trail Retention:** Every refund action records the actor's user ID, IP address, timestamp, beneficiary details snapshot, and operational justification for statutory tax auditing (FBR/PRA/SRB).
