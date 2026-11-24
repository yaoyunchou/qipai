from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# Numeric(10, 2) 可表示范围
_AMOUNT_MIN = Decimal("-99999999.99")
_AMOUNT_MAX = Decimal("99999999.99")


class PlayCompanionBase(BaseModel):
    play_date: datetime
    companion_user_id: int
    table_id: int | None = None
    duration_hours: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    amount: Decimal = Field(
        ge=_AMOUNT_MIN,
        le=_AMOUNT_MAX,
        decimal_places=2,
        description="金额：正数为赢，负数为输",
    )
    remark: str | None = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def _amount_not_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("金额不能为 0，赢或输至少记录一笔金额")
        return v

    @field_validator("play_date")
    @classmethod
    def _naive_play_date(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class PlayCompanionCreate(PlayCompanionBase):
    pass


class PlayCompanionUpdate(PlayCompanionBase):
    pass


class PlayCompanionOut(BaseModel):
    id: int
    play_date: datetime
    companion_user_id: int | None = None
    companion_username: str | None = None
    companion_name: str | None = None
    table_id: int | None = None
    table_name: str
    duration_hours: Decimal | None = None
    amount: Decimal
    remark: str | None = None
    created_by: int
    created_by_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlayCompanionSummaryOut(BaseModel):
    record_count: int
    win_total: Decimal
    """赢的合计金额（非负数）"""
    lose_total: Decimal
    """输的合计金额，以正数表示输了多少钱"""
    net_total: Decimal
    """净额 = win_total - lose_total，可为负数"""
    duration_total: Decimal


class CompanionStaffOut(BaseModel):
    id: int
    username: str
    display_name: str
    is_enabled: bool
