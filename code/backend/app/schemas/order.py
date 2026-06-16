from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class OrderOpenRequest(BaseModel):
    table_id: int
    actual_price: Decimal | None = None
    remark: str | None = Field(default=None, max_length=500)


class OrderCloseRequest(BaseModel):
    actual_price: Decimal | None = Field(default=None, ge=0)


class OrderOut(BaseModel):
    id: int
    order_no: str
    table_id: int
    table_name: str | None = None
    base_price: Decimal
    actual_price: Decimal
    billing_minutes: int | None = None
    status: OrderStatus
    remark: str | None
    opened_by: int
    opened_by_name: str | None = None
    opened_at: datetime
    closed_by: int | None
    closed_at: datetime | None

    model_config = {"from_attributes": True}
