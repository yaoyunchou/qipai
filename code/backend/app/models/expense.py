import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExpenseClaimStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ExpenseApproverStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class ExpenseApprovePermission(Base):
    __tablename__ = "expense_approve_permission"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), primary_key=True)
    granted_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )


class ExpenseClaim(Base):
    __tablename__ = "expense_claim"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    claim_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[ExpenseClaimStatus] = mapped_column(
        Enum(ExpenseClaimStatus, name="expense_claim_status", create_type=False),
        nullable=False,
        default=ExpenseClaimStatus.PENDING,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )


class ExpenseClaimAttachment(Base):
    __tablename__ = "expense_claim_attachment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("expense_claim.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="image/jpeg")
    data_base64: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )


class ExpenseClaimApprover(Base):
    __tablename__ = "expense_claim_approver"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("expense_claim.id", ondelete="CASCADE"), nullable=False
    )
    approver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False)
    status: Mapped[ExpenseApproverStatus] = mapped_column(
        Enum(ExpenseApproverStatus, name="expense_approver_status", create_type=False),
        nullable=False,
        default=ExpenseApproverStatus.PENDING,
    )
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
