from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlayCompanionRecord(Base):
    """陪玩记账：客人不够人时安排陪玩，单独记录一笔收支。"""

    __tablename__ = "play_companion_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    play_date: Mapped[date] = mapped_column(Date, nullable=False)
    table_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("room_table.id", ondelete="SET NULL"), nullable=True
    )
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    """金额：正数为赢（进账），负数为输（支出）"""
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )
