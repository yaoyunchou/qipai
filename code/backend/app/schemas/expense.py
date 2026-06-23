from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.expense import ExpenseApproverStatus, ExpenseCategory, ExpenseClaimStatus


class AttachmentIn(BaseModel):
    filename: str = Field(max_length=255)
    content_type: str = Field(default="image/jpeg", max_length=128)
    data_base64: str


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    remark: str | None = Field(default=None, max_length=500)
    category: ExpenseCategory = Field(default=ExpenseCategory.FIXED)
    attachments: list[AttachmentIn] = Field(default_factory=list)


class ExpenseUpdate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    remark: str | None = Field(default=None, max_length=500)
    category: ExpenseCategory = Field(default=ExpenseCategory.FIXED)
    attachments: list[AttachmentIn] = Field(default_factory=list)


class ApproverAction(BaseModel):
    comment: str = Field(min_length=1, max_length=500)


class AttachmentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    data_base64: str

    model_config = {"from_attributes": True}


class ApproverRecordOut(BaseModel):
    id: int
    approver_id: int
    approver_name: str | None = None
    status: ExpenseApproverStatus
    comment: str | None
    acted_at: datetime | None

    model_config = {"from_attributes": True}


class ExpenseClaimOut(BaseModel):
    id: int
    claim_no: str
    applicant_id: int
    applicant_name: str | None = None
    amount: Decimal
    remark: str | None
    category: ExpenseCategory = ExpenseCategory.FIXED
    status: ExpenseClaimStatus
    submitted_at: datetime
    attachments: list[AttachmentOut] = []
    approvers: list[ApproverRecordOut] = []

    model_config = {"from_attributes": True}


class SelectableApproverOut(BaseModel):
    id: int
    display_name: str
    role: str


class ApprovePermissionOut(BaseModel):
    user_id: int
    username: str
    display_name: str
    role: str
    can_approve: bool


class ApprovePermissionUpdate(BaseModel):
    user_ids: list[int]


class CategorySummary(BaseModel):
    category: ExpenseCategory
    claim_count: int
    amount_total: Decimal


class ExpenseReportSummary(BaseModel):
    period: str
    start_date: str
    end_date: str
    claim_count: int
    amount_total: Decimal
    by_category: list[CategorySummary] = []
