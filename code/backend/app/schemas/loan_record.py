from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# Numeric(12, 2) 可表示范围
_AMOUNT_MIN = Decimal("-9999999999.99")
_AMOUNT_MAX = Decimal("9999999999.99")


class LoanRecordBase(BaseModel):
    loan_date: date
    borrower: str = Field(min_length=1, max_length=64, description="借款人（客人姓名/称呼）")
    contact: str | None = Field(default=None, max_length=64, description="联系方式，选填")
    amount: Decimal = Field(
        ge=_AMOUNT_MIN,
        le=_AMOUNT_MAX,
        decimal_places=2,
        description="金额：正数为借出（客人欠款），负数为还钱",
    )
    remark: str | None = Field(default=None, max_length=500)

    @field_validator("borrower")
    @classmethod
    def _borrower_not_blank(cls, v: str) -> str:
        name = v.strip()
        if not name:
            raise ValueError("请填写借款人")
        return name

    @field_validator("contact")
    @classmethod
    def _contact_strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = v.strip()
        return value or None

    @field_validator("amount")
    @classmethod
    def _amount_not_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("金额不能为 0，借出或还钱至少记录一笔金额")
        return v


class LoanRecordCreate(LoanRecordBase):
    pass


class LoanRecordUpdate(LoanRecordBase):
    pass


class LoanRecordOut(BaseModel):
    id: int
    loan_date: date
    borrower: str
    contact: str | None = None
    amount: Decimal
    remark: str | None = None
    created_by: int
    created_by_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoanSummaryOut(BaseModel):
    record_count: int
    lent_total: Decimal
    """借出合计（非负数）"""
    repaid_total: Decimal
    """还钱合计，以正数表示已还多少钱"""
    balance_total: Decimal
    """未还余额 = 借出合计 - 还钱合计，可为负数（多还了）"""


class LoanBorrowerSummaryOut(BaseModel):
    borrower: str
    lent_total: Decimal
    """该客人借出合计（非负数）"""
    repaid_total: Decimal
    """该客人还钱合计（非负数）"""
    balance: Decimal
    """该客人未还余额 = lent_total - repaid_total"""
    record_count: int
    last_date: date
    """最近一次借款/还款日期"""


class LoanBorrowerDetailOut(BaseModel):
    """单个客人的总账 + 全部流水（用于「点进去看明细」）。"""

    borrower: str
    lent_total: Decimal
    """该客人借出合计（非负数）"""
    repaid_total: Decimal
    """该客人还钱合计（非负数）"""
    balance: Decimal
    """该客人未还余额 = lent_total - repaid_total，可为负数（多还了）"""
    record_count: int
    last_date: date | None = None
    """最近一次借款/还款日期"""
    records: list["LoanRecordOut"]
    """该客人的全部流水，按日期倒序"""


LoanBorrowerDetailOut.model_rebuild()
