from decimal import Decimal

from pydantic import BaseModel, Field


class StoreConfigOut(BaseModel):
    base_price: Decimal
    enable_timing: bool
    billing_unit_minutes: int
    min_billing_units: int
    cashier_allow_custom_price: bool
    cashier_allow_export: bool
    cashier_report_months: int | None
    admin_report_days: int | None

    model_config = {"from_attributes": True}


class StoreConfigUpdate(BaseModel):
    base_price: Decimal | None = Field(default=None, ge=0)
    enable_timing: bool | None = None
    billing_unit_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    min_billing_units: int | None = Field(default=None, ge=1, le=999)
    cashier_allow_custom_price: bool | None = None
    cashier_allow_export: bool | None = None
    cashier_report_months: int | None = None
    admin_report_days: int | None = None
