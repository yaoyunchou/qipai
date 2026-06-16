from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TableBoardItem(BaseModel):
    id: int
    name: str
    sort_order: int
    is_enabled: bool
    status: str  # IDLE | OCCUPIED
    open_order_id: int | None = None
    open_order_no: str | None = None
    actual_price: Decimal | None = None
    opened_at: datetime | None = None
    billing_minutes: int | None = None
    enable_timing: bool = False
    billing_unit_minutes: int = 60
    unit_price: Decimal | None = None


class TableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    sort_order: int = 0
    is_enabled: bool = True


class TableUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_enabled: bool | None = None
