from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CompanionLoanCreate(BaseModel):
    companion_user_id: int | None = None
    occurred_at: datetime
    amount: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    remark: str | None = Field(default=None, max_length=500)

    @field_validator("occurred_at")
    @classmethod
    def _naive_time(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class CompanionLoanOut(BaseModel):
    id: int
    companion_user_id: int
    companion_username: str | None = None
    companion_name: str | None = None
    direction: str
    amount: Decimal
    status: str
    occurred_at: datetime
    remark: str | None = None
    created_by: int
    created_by_name: str | None = None
    confirmed_by: int | None = None
    confirmed_by_name: str | None = None
    confirmed_at: datetime | None = None
    created_at: datetime


class CompanionLoanSummaryOut(BaseModel):
    companion_user_id: int | None = None
    lend_total: Decimal
    repay_total: Decimal
    balance: Decimal
    pending_count: int


class CompanionBalanceOut(BaseModel):
    companion_user_id: int
    username: str
    display_name: str
    is_enabled: bool
    lend_total: Decimal
    repay_total: Decimal
    balance: Decimal
    pending_count: int
