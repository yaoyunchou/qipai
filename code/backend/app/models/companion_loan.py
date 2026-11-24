from datetime import datetime
from decimal import Decimal
import enum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CompanionLoanDirection(str, enum.Enum):
    LEND = "LEND"
    REPAY = "REPAY"


class CompanionLoanStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"


class CompanionLoan(Base):
    """陪玩向股东借款。未确认的记录不计入欠款。"""

    __tablename__ = "companion_loan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    companion_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CompanionLoanStatus.PENDING.value)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False)
    confirmed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )
