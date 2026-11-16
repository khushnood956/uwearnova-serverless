"""
Offline Sales & Point of Sale (POS) Module
Records in-person physical store/shop sales, deducts inventory, and tracks revenue.
"""

from app.modules.offline_sales.models import OfflineSale, OfflineSaleItem

__all__ = ["OfflineSale", "OfflineSaleItem"]
