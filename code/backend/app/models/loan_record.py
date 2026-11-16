from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LoanRecord(Base):
    """借钱还钱：客人临时借款与还款，独立成账。

    金额带符号：正数为借出（客人欠店里），负数为还钱（客人还款）。
    """

    __tablename__ = "loan_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    loan_date: Mapped[date] = mapped_column(Date, nullable=False)
    borrower: Mapped[str] = mapped_column(String(64), nullable=False)
    contact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    """金额：正数为借出，负数为还钱"""
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )
