"""
Courier Provider Adapter Interface & Tracking Integrations (Module M15)
Decouples logistics fulfillment and parcel consignment tracking behind a unified interface.
Adheres strictly to the architectural constraint: Never invent courier credentials or claim
live automated tracking without a verified carrier provider integration.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class CourierTrackingCheckpoint(BaseModel):
    """Normalized checkpoint milestone along a parcel's transit path."""
    status: str
    location: Optional[str] = None
    description: str
    occurred_at: datetime
    raw_status: Optional[str] = None


class CourierTrackingResult(BaseModel):
    """Normalized carrier response representing live tracking inquiry."""
    courier_code: str
    tracking_number: str
    current_status: str
    checkpoints: List[CourierTrackingCheckpoint] = Field(default_factory=list)
    estimated_delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    is_delivered: bool = False


class ConsignmentResult(BaseModel):
    """Normalized response upon booking a parcel consignment with a carrier."""
    courier_code: str
    courier_name: str
    tracking_number: str
    tracking_url: Optional[str] = None
    booking_reference: Optional[str] = None
    label_url: Optional[str] = None
    estimated_delivery_days_min: int = 2
    estimated_delivery_days_max: int = 4
    metadata: dict = Field(default_factory=dict)


class BaseCourierTrackingProvider(ABC):
    """
    Abstract interface for logistics carriers in Pakistan and international destinations.
    """

    @property
    @abstractmethod
    def courier_code(self) -> str:
        """Unique carrier identifier."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable carrier name."""
        pass

    @abstractmethod
    def generate_tracking_url(self, tracking_number: str) -> Optional[str]:
        """Construct public web URL where customers can view live delivery milestones."""
        pass

    @abstractmethod
    async def book_consignment(
        self,
        shipment_number: str,
        destination_city: str,
        destination_address: dict,
        cod_amount: Decimal,
        weight_grams: int,
        order_number: str,
        customer_phone: str,
        customer_name: str,
        manual_tracking_number: Optional[str] = None,
    ) -> ConsignmentResult:
        """Register or format a consignment note for the carrier."""
        pass

    @abstractmethod
    async def fetch_tracking_updates(self, tracking_number: str) -> CourierTrackingResult:
        """Query carrier tracking API or return current logged status."""
        pass


class ManualCourierProvider(BaseCourierTrackingProvider):
    """
    Standard Pakistani Courier Adapter for manual booking and physical consignment notes.
    Supports TCS, Leopards, Trax, Call Courier, M&P, and PostEx tracking URLs
    without fabricating API automated calls.
    """

    CARRIER_NAMES: Dict[str, str] = {
        "tcs": "TCS Express",
        "leopards": "Leopards Courier",
        "trax": "Trax Logistics",
        "call_courier": "Call Courier",
        "postex": "PostEx Logistics",
        "mnp": "M&P Express Logistics",
        "manual": "Direct Logistics Partner",
    }

    TRACKING_URL_TEMPLATES: Dict[str, str] = {
        "tcs": "https://www.tcsexpress.com/tracking?consignmentNo={tracking_number}",
        "leopards": "https://www.leopardscourier.com/tracking?track={tracking_number}",
        "trax": "https://trax.pk/tracking?cn={tracking_number}",
        "call_courier": "https://callcourier.com.pk/tracking/?tc={tracking_number}",
        "postex": "https://postex.pk/tracking?cn={tracking_number}",
        "mnp": "https://mulphilog.com/tracking?consignment={tracking_number}",
    }

    def __init__(self, carrier_code: str = "manual"):
        self._code = carrier_code.lower().strip()

    @property
    def courier_code(self) -> str:
        return self._code

    @property
    def display_name(self) -> str:
        return self.CARRIER_NAMES.get(self._code, f"Courier Partner ({self._code.upper()})")

    def generate_tracking_url(self, tracking_number: str) -> Optional[str]:
        if not tracking_number:
            return None
        template = self.TRACKING_URL_TEMPLATES.get(self._code)
        if template:
            return template.format(tracking_number=tracking_number.strip())
        return None

    async def book_consignment(
        self,
        shipment_number: str,
        destination_city: str,
        destination_address: dict,
        cod_amount: Decimal,
        weight_grams: int,
        order_number: str,
        customer_phone: str,
        customer_name: str,
        manual_tracking_number: Optional[str] = None,
    ) -> ConsignmentResult:
        # For manual courier, either use provided airway bill or generate consignment reference
        tracking_num = manual_tracking_number or f"{self._code.upper()}-{shipment_number.replace('SHP-', '')}"
        tracking_url = self.generate_tracking_url(tracking_num)

        return ConsignmentResult(
            courier_code=self._code,
            courier_name=self.display_name,
            tracking_number=tracking_num,
            tracking_url=tracking_url,
            booking_reference=f"BK-{shipment_number}",
            estimated_delivery_days_min=2,
            estimated_delivery_days_max=4,
            metadata={
                "order_number": order_number,
                "destination_city": destination_city,
                "cod_amount": str(cod_amount),
            },
        )

    async def fetch_tracking_updates(self, tracking_number: str) -> CourierTrackingResult:
        # Manual provider does not have automated pull; updates are managed through staff checkpoint events
        return CourierTrackingResult(
            courier_code=self._code,
            tracking_number=tracking_number,
            current_status="dispatched",
            checkpoints=[
                CourierTrackingCheckpoint(
                    status="dispatched",
                    location=None,
                    description=f"Consignment {tracking_number} booked with {self.display_name}",
                    occurred_at=datetime.now(timezone.utc),
                )
            ],
            is_delivered=False,
        )


class MockCourierProvider(BaseCourierTrackingProvider):
    """
    Test harness carrier provider for automated verification and test pipelines.
    Simulates consignment creation and complete multi-stop tracking journeys.
    """

    def __init__(self, carrier_code: str = "mock"):
        self._code = carrier_code

    @property
    def courier_code(self) -> str:
        return "mock"

    @property
    def display_name(self) -> str:
        return "UniNova Automated Test Logistics"

    def generate_tracking_url(self, tracking_number: str) -> Optional[str]:
        return f"https://mock-courier.local/tracking/{tracking_number}"

    async def book_consignment(
        self,
        shipment_number: str,
        destination_city: str,
        destination_address: dict,
        cod_amount: Decimal,
        weight_grams: int,
        order_number: str,
        customer_phone: str,
        customer_name: str,
        manual_tracking_number: Optional[str] = None,
    ) -> ConsignmentResult:
        tracking_num = manual_tracking_number or f"MOCK-CN-{shipment_number.replace('SHP-', '')}"
        return ConsignmentResult(
            courier_code="mock",
            courier_name=self.display_name,
            tracking_number=tracking_num,
            tracking_url=self.generate_tracking_url(tracking_num),
            booking_reference=f"MOCK-BK-{shipment_number}",
            label_url=f"https://mock-courier.local/labels/{tracking_num}.pdf",
            estimated_delivery_days_min=1,
            estimated_delivery_days_max=3,
            metadata={"weight_grams": weight_grams, "city": destination_city},
        )

    async def fetch_tracking_updates(self, tracking_number: str) -> CourierTrackingResult:
        now = datetime.now(timezone.utc)
        return CourierTrackingResult(
            courier_code="mock",
            tracking_number=tracking_number,
            current_status="in_transit",
            checkpoints=[
                CourierTrackingCheckpoint(
                    status="dispatched",
                    location="Lahore Sort Facility",
                    description="Parcel scanned at origin sort hub",
                    occurred_at=now,
                ),
                CourierTrackingCheckpoint(
                    status="in_transit",
                    location="Islamabad Regional Terminal",
                    description="Parcel arrived at destination sort center",
                    occurred_at=now,
                ),
            ],
            is_delivered=False,
        )


class UnconfiguredCourierProvider(BaseCourierTrackingProvider):
    """
    Guards against attempting to invoke external third-party courier APIs when no
    active merchant credentials (API keys, account numbers, password tokens) exist.
    """

    def __init__(self, requested_carrier: str):
        self._carrier = requested_carrier

    @property
    def courier_code(self) -> str:
        return self._carrier

    @property
    def display_name(self) -> str:
        return f"Unconfigured Courier ({self._carrier})"

    def generate_tracking_url(self, tracking_number: str) -> Optional[str]:
        return None

    async def book_consignment(self, **kwargs) -> ConsignmentResult:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"COURIER_API_NOT_CONFIGURED: Live API credentials for courier '{self._carrier}' are not configured. "
                "Use manual courier mode or enter a physical tracking reference."
            ),
        )

    async def fetch_tracking_updates(self, tracking_number: str) -> CourierTrackingResult:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"COURIER_API_NOT_CONFIGURED: Live tracking API for '{self._carrier}' is not configured.",
        )


def get_courier_provider(courier_code: Optional[str] = None) -> BaseCourierTrackingProvider:
    """
    Factory resolving active courier tracking and consignment provider.
    """
    code = (courier_code or "manual").lower().strip()
    if code in ("manual", "tcs", "leopards", "trax", "call_courier", "postex", "mnp"):
        return ManualCourierProvider(carrier_code=code)
    if code == "mock":
        return MockCourierProvider()
    return UnconfiguredCourierProvider(requested_carrier=code)
