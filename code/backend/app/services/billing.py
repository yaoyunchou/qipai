import math
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.core.timezone import now_cn


def calc_timing_bill(
    opened_at: datetime,
    closed_at: datetime,
    unit_price: Decimal,
    billing_unit_minutes: int,
    min_billing_units: int = 1,
) -> tuple[Decimal, int]:
    """按开单时长计算费用。不足一个计费单位按一个单位向上取整，并受最低单位数约束。"""
    if billing_unit_minutes <= 0:
        billing_unit_minutes = 60
    min_units = max(1, min_billing_units)
    elapsed_minutes = max(0.0, (closed_at - opened_at).total_seconds() / 60)
    units = max(min_units, math.ceil(elapsed_minutes / billing_unit_minutes))
    billing_minutes = units * billing_unit_minutes
    amount = (unit_price * Decimal(units)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return amount, billing_minutes


def elapsed_minutes(opened_at: datetime, now: datetime | None = None) -> int:
    ref = now or now_cn()
    return max(0, int((ref - opened_at).total_seconds() // 60))
