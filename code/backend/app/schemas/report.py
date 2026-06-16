from decimal import Decimal

from pydantic import BaseModel


class ReportSummary(BaseModel):
    period: str  # day | week | month
    start_date: str
    end_date: str
    order_count: int
    base_price_total: Decimal
    actual_price_total: Decimal
