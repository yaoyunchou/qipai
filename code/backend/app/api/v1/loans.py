"""借钱还钱（独立模块）。

场景：客人有时需要向店里借钱、之后还钱，这部分流水独立成账，
不混入台位订单、报销与陪玩记账。

权限：
- 收银员 / 经理 / 超管：录入、查看明细、修改（非超管仅能改自己录入的记录）
- 删除仅超管可操作，录入人录错也不能自行删除
- 股东：仅可查看汇总（借出 / 还钱 / 未还余额），不可见明细

金额语义：正数为借出（客人欠店里），负数为还钱（客人还款）。
"""
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.timezone import now_cn
from app.models import LoanRecord, SysUser, UserRole
from app.schemas.loan_record import (
    LoanBorrowerDetailOut,
    LoanBorrowerSummaryOut,
    LoanRecordCreate,
    LoanRecordOut,
    LoanRecordUpdate,
    LoanSummaryOut,
)

router = APIRouter(prefix="/loans", tags=["loans"])

EditorUser = Annotated[
    SysUser, Depends(require_roles(UserRole.CASHIER, UserRole.MANAGER, UserRole.ADMIN))
]

VIEWER_ROLES = (UserRole.CASHIER, UserRole.MANAGER, UserRole.ADMIN)


def _to_out(record: LoanRecord, db) -> LoanRecordOut:
    creator = db.get(SysUser, record.created_by)
    return LoanRecordOut(
        id=record.id,
        loan_date=record.loan_date,
        borrower=record.borrower,
        contact=record.contact,
        amount=record.amount,
        remark=record.remark,
        created_by=record.created_by,
        created_by_name=creator.display_name if creator else None,
        created_at=record.created_at,
    )


def _ensure_editable(record: LoanRecord, user: SysUser) -> None:
    if user.role == UserRole.ADMIN:
        return
    if record.created_by != user.id:
        raise HTTPException(status_code=403, detail="只能修改自己录入的借钱记录")


@router.get("/summary", response_model=LoanSummaryOut)
def summary(
    db: DbSession,
    user: CurrentUser,
    start: date | None = Query(None, description="起始日期 YYYY-MM-DD"),
    end: date | None = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """借钱汇总（股东可用）：借出 / 还钱 / 未还余额。"""
    amount = LoanRecord.amount
    q = select(
        func.count(LoanRecord.id),
        func.coalesce(func.sum(case((amount > 0, amount), else_=0)), 0),
        func.coalesce(func.sum(case((amount < 0, -amount), else_=0)), 0),
        func.coalesce(func.sum(amount), 0),
    )
    if start:
        q = q.where(LoanRecord.loan_date >= start)
    if end:
        q = q.where(LoanRecord.loan_date <= end)
    row = db.execute(q).one()
    return LoanSummaryOut(
        record_count=int(row[0] or 0),
        lent_total=Decimal(str(row[1])),
        repaid_total=Decimal(str(row[2])),
        balance_total=Decimal(str(row[3])),
    )


@router.get("/borrowers", response_model=list[LoanBorrowerSummaryOut])
def borrower_summary(
    db: DbSession,
    user: CurrentUser,
    start: date | None = Query(None, description="起始日期 YYYY-MM-DD"),
    end: date | None = Query(None, description="结束日期 YYYY-MM-DD"),
    only_pending: bool = Query(False, description="只看还有未还款余额的客人"),
    limit: int = Query(100, le=500),
):
    """按客人聚合的欠款余额（股东可用）：谁还欠多少，一眼看清。"""
    amount = LoanRecord.amount
    q = select(
        LoanRecord.borrower,
        func.coalesce(func.sum(case((amount > 0, amount), else_=0)), 0),
        func.coalesce(func.sum(case((amount < 0, -amount), else_=0)), 0),
        func.coalesce(func.sum(amount), 0),
        func.count(LoanRecord.id),
        func.max(LoanRecord.loan_date),
    ).group_by(LoanRecord.borrower)
    if start:
        q = q.where(LoanRecord.loan_date >= start)
    if end:
        q = q.where(LoanRecord.loan_date <= end)
    if only_pending:
        q = q.having(func.coalesce(func.sum(amount), 0) != 0)
    q = q.order_by(func.coalesce(func.sum(amount), 0).desc(), LoanRecord.borrower).limit(limit)
    rows = db.execute(q).all()
    return [
        LoanBorrowerSummaryOut(
            borrower=row[0],
            lent_total=Decimal(str(row[1])),
            repaid_total=Decimal(str(row[2])),
            balance=Decimal(str(row[3])),
            record_count=int(row[4] or 0),
            last_date=row[5],
        )
        for row in rows
    ]


@router.get("/borrowers/detail", response_model=LoanBorrowerDetailOut)
def borrower_detail(
    db: DbSession,
    user: CurrentUser,
    borrower: str = Query(..., min_length=1, description="客人姓名（精确匹配）"),
):
    """单个客人的总账 + 全部流水（股东可用）。

    余额与明细都按**全部历史**计算，不受日期筛选影响，
    否则「上月借、本月还」会被算错。
    """
    name = borrower.strip()
    amount = LoanRecord.amount

    agg = db.execute(
        select(
            func.count(LoanRecord.id),
            func.coalesce(func.sum(case((amount > 0, amount), else_=0)), 0),
            func.coalesce(func.sum(case((amount < 0, -amount), else_=0)), 0),
            func.coalesce(func.sum(amount), 0),
            func.max(LoanRecord.loan_date),
        ).where(LoanRecord.borrower == name)
    ).one()

    rows = db.scalars(
        select(LoanRecord)
        .where(LoanRecord.borrower == name)
        .order_by(LoanRecord.loan_date.desc(), LoanRecord.id.desc())
    ).all()

    return LoanBorrowerDetailOut(
        borrower=name,
        lent_total=Decimal(str(agg[1])),
        repaid_total=Decimal(str(agg[2])),
        balance=Decimal(str(agg[3])),
        record_count=int(agg[0] or 0),
        last_date=agg[4],
        records=[_to_out(r, db) for r in rows],
    )


@router.get("", response_model=list[LoanRecordOut])
def list_records(
    db: DbSession,
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
    borrower: str | None = Query(None, description="按借款人模糊筛选"),
    limit: int = Query(200, le=500),
):
    if user.role not in VIEWER_ROLES:
        raise HTTPException(status_code=403, detail="仅可查看借钱汇总")

    q = (
        select(LoanRecord)
        .order_by(LoanRecord.loan_date.desc(), LoanRecord.id.desc())
        .limit(limit)
    )
    if start:
        q = q.where(LoanRecord.loan_date >= start)
    if end:
        q = q.where(LoanRecord.loan_date <= end)
    if borrower:
        q = q.where(LoanRecord.borrower.ilike(f"%{borrower.strip()}%"))
    records = db.scalars(q).all()
    return [_to_out(r, db) for r in records]


@router.post("", response_model=LoanRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(body: LoanRecordCreate, db: DbSession, user: EditorUser):
    record = LoanRecord(
        loan_date=body.loan_date,
        borrower=body.borrower,
        contact=body.contact,
        amount=body.amount,
        remark=body.remark,
        created_by=user.id,
        created_at=now_cn(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.put("/{record_id}", response_model=LoanRecordOut)
def update_record(
    record_id: int,
    body: LoanRecordUpdate,
    db: DbSession,
    user: EditorUser,
):
    record = db.get(LoanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _ensure_editable(record, user)

    record.loan_date = body.loan_date
    record.borrower = body.borrower
    record.contact = body.contact
    record.amount = body.amount
    record.remark = body.remark
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.delete("/{record_id}")
def delete_record(record_id: int, db: DbSession, user: EditorUser):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以删除借还记录")
    record = db.get(LoanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}
