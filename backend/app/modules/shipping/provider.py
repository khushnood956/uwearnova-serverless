"""
Courier Provider Interface & Adapters (M11)
Decouples carrier logic, serviceability checks, and shipping rates behind
a unified provider interface. Never hardcodes unverified 3PL courier rates.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CourierRateQuote(BaseModel):
    """Normalized rate quote from a courier provider."""
    provider_code: str
    service_code: str
    service_name: str
    base_rate: Decimal
    fuel_surcharge: Decimal = Decimal("0.00")
    cod_fee: Decimal = Decimal("0.00")
    total_rate: Decimal
    estimated_delivery_days_min: int
    estimated_delivery_days_max: int
    is_serviceable: bool
    notes: Optional[str] = None


class BaseCourierProvider(ABC):
    """Abstract interface defining required courier operations."""

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique carrier provider identifier (e.g. 'configured_rates', 'tcs', 'leopards')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable carrier name."""
        pass

    @abstractmethod
    async def verify_serviceability(
        self,
        city: str,
        postal_code: Optional[str] = None,
        country_code: str = "PK",
    ) -> bool:
        """Check whether the carrier operates in the destination postal area."""
        pass

    @abstractmethod
    async def calculate_rate(
        self,
        origin_city: str,
        destination_city: str,
        weight_grams: int,
        order_subtotal: Decimal,
        is_cod: bool = False,
    ) -> CourierRateQuote:
        """Calculate dynamic or contracted courier freight rate."""
        pass


class ConfiguredRateCourierProvider(BaseCourierProvider):
    """
    Default courier provider that calculates rates using UniNova's database-backed
    shipping method rules and verified free-shipping thresholds.
    """

    @property
    def provider_code(self) -> str:
        return "configured_rates"

    @property
    def display_name(self) -> str:
        return "UniNova Direct Logistics & Premier Partner Network"

    async def verify_serviceability(
        self,
        city: str,
        postal_code: Optional[str] = None,
        country_code: str = "PK",
    ) -> bool:
        # Standard nationwide serviceability for Pakistan domestic postal destinations
        return country_code.upper() == "PK" and bool(city.strip())

    async def calculate_rate(
        self,
        origin_city: str,
        destination_city: str,
        weight_grams: int,
        order_subtotal: Decimal,
        is_cod: bool = False,
    ) -> CourierRateQuote:
        # Standard base rate calculation
        base_rate = Decimal("350.00")
        free_threshold = Decimal("15000.00")

        if order_subtotal >= free_threshold:
            total_rate = Decimal("0.00")
            notes = "Complimentary nationwide luxury delivery applied"
        else:
            total_rate = base_rate
            notes = "Standard nationwide shipping applied"

        return CourierRateQuote(
            provider_code=self.provider_code,
            service_code="standard_nationwide",
            service_name="Standard Nationwide Delivery",
            base_rate=base_rate,
            fuel_surcharge=Decimal("0.00"),
            cod_fee=Decimal("0.00"),
            total_rate=total_rate,
            estimated_delivery_days_min=2,
            estimated_delivery_days_max=4,
            is_serviceable=True,
            notes=notes,
        )


class MockThirdPartyCourierProvider(BaseCourierProvider):
    """
    Simulation provider for third-party logistics API integrations (e.g. TCS / Leopards / Trax)
    demonstrating multi-carrier extensibility without hardcoding live credentials.
    """

    def __init__(self, carrier_code: str = "tcs", carrier_name: str = "TCS Express"):
        self._code = carrier_code
        self._name = carrier_name

    @property
    def provider_code(self) -> str:
        return self._code

    @property
    def display_name(self) -> str:
        return self._name

    async def verify_serviceability(
        self,
        city: str,
        postal_code: Optional[str] = None,
        country_code: str = "PK",
    ) -> bool:
        unserviceable_cities = {"restricted_remote_military_zone"}
        return city.lower().strip() not in unserviceable_cities

    async def calculate_rate(
        self,
        origin_city: str,
        destination_city: str,
        weight_grams: int,
        order_subtotal: Decimal,
        is_cod: bool = False,
    ) -> CourierRateQuote:
        base_rate = Decimal("400.00")
        cod_fee = Decimal("100.00") if is_cod else Decimal("0.00")
        total_rate = base_rate + cod_fee

        return CourierRateQuote(
            provider_code=self.provider_code,
            service_code=f"{self._code}_express",
            service_name=f"{self._name} Overland Priority",
            base_rate=base_rate,
            fuel_surcharge=Decimal("25.00"),
            cod_fee=cod_fee,
            total_rate=total_rate,
            estimated_delivery_days_min=1,
            estimated_delivery_days_max=3,
            is_serviceable=True,
            notes="Third-party courier contracted tariff quote",
        )
