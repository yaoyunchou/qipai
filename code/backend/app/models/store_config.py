from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SysStoreConfig(Base):
    __tablename__ = "sys_store_config"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    enable_timing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    billing_unit_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    min_billing_units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cashier_allow_custom_price: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cashier_allow_export: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cashier_report_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_report_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )
