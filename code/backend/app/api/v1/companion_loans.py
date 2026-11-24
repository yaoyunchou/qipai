"""陪玩向股东借款。

股东或超管记放款，陪玩登录后自己确认。陪玩发起还款，股东或超管确认。
未确认的记录不进欠款。客人借钱不走这里。
"""
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select

from app.core.deps import DbSession, require_roles
from app.core.timezone import now_cn
from app.models import CompanionLoan, CompanionLoanDirection, CompanionLoanStatus, SysUser, UserRole
from app.schemas.companion_loan import (
    CompanionBalanceOut,
    CompanionLoanCreate,
    CompanionLoanOut,
    CompanionLoanSummaryOut,
)

router = APIRouter(prefix="/companion-loans", tags=["companion-loans"])

LenderUser = Annotated[SysUser, Depends(require_roles(UserRole.SHAREHOLDER, UserRole.ADMIN))]
ViewerUser = Annotated[
    SysUser, Depends(require_roles(UserRole.SHAREHOLDER, UserRole.ADMIN, UserRole.COMPANION))
]


def _name(db, user_id: int | None) -> SysUser | None:
    if not user_id:
        return None
    return db.get(SysUser, user_id)


def _to_out(record: CompanionLoan, db) -> CompanionLoanOut:
    companion = _name(db, record.companion_user_id)
    creator = _name(db, record.created_by)
    confirmer = _name(db, record.confirmed_by)
    return CompanionLoanOut(
        id=record.id,
        companion_user_id=record.companion_user_id,
        companion_username=companion.username if companion else None,
        companion_name=companion.display_name if companion else None,
        direction=record.direction,
        amount=record.amount,
        status=record.status,
        occurred_at=record.occurred_at,
        remark=record.remark,
        created_by=record.created_by,
        created_by_name=creator.display_name if creator else None,
        confirmed_by=record.confirmed_by,
        confirmed_by_name=confirmer.display_name if confirmer else None,
        confirmed_at=record.confirmed_at,
        created_at=record.created_at,
    )


def _require_active_companion(db, companion_user_id: int) -> SysUser:
    companion = db.get(SysUser, companion_user_id)
    if not companion or companion.role != UserRole.COMPANION:
        raise HTTPException(status_code=400, detail="请选择陪玩员工")
    if not companion.is_enabled:
        raise HTTPException(status_code=400, detail="该陪玩已停用")
    return companion


def _scope(user: SysUser, companion_user_id: int | None) -> int | None:
    if user.role == UserRole.COMPANION:
        return user.id
    return companion_user_id


@router.get("/balances", response_model=list[CompanionBalanceOut])
def balances(db: DbSession, user: ViewerUser):
    """每个陪玩一条：只统计已确认的放款和还款。"""
    staff_q = select(SysUser).where(SysUser.role == UserRole.COMPANION).order_by(SysUser.username)
    if user.role == UserRole.COMPANION:
        staff_q = staff_q.where(SysUser.id == user.id)
    staff = db.scalars(staff_q).all()
    if not staff:
        return []

    amount = CompanionLoan.amount
    confirmed = CompanionLoan.status == CompanionLoanStatus.CONFIRMED.value
    rows = db.execute(
        select(
            CompanionLoan.companion_user_id,
            func.coalesce(func.sum(case((confirmed & (CompanionLoan.direction == CompanionLoanDirection.LEND.value), amount), else_=0)), 0),
            func.coalesce(func.sum(case((confirmed & (CompanionLoan.direction == CompanionLoanDirection.REPAY.value), amount), else_=0)), 0),
            func.coalesce(func.sum(case((CompanionLoan.status == CompanionLoanStatus.PENDING.value, 1), else_=0)), 0),
        )
        .where(CompanionLoan.companion_user_id.in_([s.id for s in staff]))
        .group_by(CompanionLoan.companion_user_id)
    ).all()
    by_id = {row[0]: row for row in rows}
    result: list[CompanionBalanceOut] = []
    for person in staff:
        row = by_id.get(person.id)
        lend = Decimal(str(row[1])) if row else Decimal("0")
        repay = Decimal(str(row[2])) if row else Decimal("0")
        pending = int(row[3] or 0) if row else 0
        result.append(
            CompanionBalanceOut(
                companion_user_id=person.id,
                username=person.username,
                display_name=person.display_name,
                is_enabled=person.is_enabled,
                lend_total=lend,
                repay_total=repay,
                balance=lend - repay,
                pending_count=pending,
            )
        )
    return result


@router.get("/summary", response_model=CompanionLoanSummaryOut)
def summary(
    db: DbSession,
    user: ViewerUser,
    companion_user_id: int | None = Query(None),
):
    scoped = _scope(user, companion_user_id)
    amount = CompanionLoan.amount
    confirmed = CompanionLoan.status == CompanionLoanStatus.CONFIRMED.value
    q = select(
        func.coalesce(func.sum(case((confirmed & (CompanionLoan.direction == CompanionLoanDirection.LEND.value), amount), else_=0)), 0),
        func.coalesce(func.sum(case((confirmed & (CompanionLoan.direction == CompanionLoanDirection.REPAY.value), amount), else_=0)), 0),
        func.coalesce(func.sum(case((CompanionLoan.status == CompanionLoanStatus.PENDING.value, 1), else_=0)), 0),
    )
    if scoped:
        q = q.where(CompanionLoan.companion_user_id == scoped)
    row = db.execute(q).one()
    lend = Decimal(str(row[0]))
    repay = Decimal(str(row[1]))
    return CompanionLoanSummaryOut(
        companion_user_id=scoped,
        lend_total=lend,
        repay_total=repay,
        balance=lend - repay,
        pending_count=int(row[2] or 0),
    )


@router.get("", response_model=list[CompanionLoanOut])
def list_loans(
    db: DbSession,
    user: ViewerUser,
    companion_user_id: int | None = None,
    limit: int = Query(200, le=500),
):
    scoped = _scope(user, companion_user_id)
    q = select(CompanionLoan).order_by(CompanionLoan.occurred_at.desc(), CompanionLoan.id.desc()).limit(limit)
    if scoped:
        q = q.where(CompanionLoan.companion_user_id == scoped)
    return [_to_out(row, db) for row in db.scalars(q).all()]


@router.post("/lend", response_model=CompanionLoanOut, status_code=status.HTTP_201_CREATED)
def create_lend(body: CompanionLoanCreate, db: DbSession, user: LenderUser):
    if body.companion_user_id is None:
        raise HTTPException(status_code=400, detail="请选择陪玩")
    _require_active_companion(db, body.companion_user_id)
    record = CompanionLoan(
        companion_user_id=body.companion_user_id,
        direction=CompanionLoanDirection.LEND.value,
        amount=body.amount,
        status=CompanionLoanStatus.PENDING.value,
        occurred_at=body.occurred_at,
        remark=body.remark,
        created_by=user.id,
        created_at=now_cn(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.post("/repay", response_model=CompanionLoanOut, status_code=status.HTTP_201_CREATED)
def create_repay(body: CompanionLoanCreate, db: DbSession, user: ViewerUser):
    if user.role != UserRole.COMPANION:
        raise HTTPException(status_code=403, detail="还款由陪玩本人发起")
    record = CompanionLoan(
        companion_user_id=user.id,
        direction=CompanionLoanDirection.REPAY.value,
        amount=body.amount,
        status=CompanionLoanStatus.PENDING.value,
        occurred_at=body.occurred_at,
        remark=body.remark,
        created_by=user.id,
        created_at=now_cn(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.post("/{loan_id}/confirm", response_model=CompanionLoanOut)
def confirm_loan(loan_id: int, db: DbSession, user: ViewerUser):
    record = db.get(CompanionLoan, loan_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.status == CompanionLoanStatus.CONFIRMED.value:
        raise HTTPException(status_code=400, detail="这条已经确认过了")
    if record.direction == CompanionLoanDirection.LEND.value:
        if user.role != UserRole.COMPANION or user.id != record.companion_user_id:
            raise HTTPException(status_code=403, detail="放款要由这笔账的陪玩自己确认")
    elif user.role not in (UserRole.SHAREHOLDER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="还款要由股东或管理员确认")
    record.status = CompanionLoanStatus.CONFIRMED.value
    record.confirmed_by = user.id
    record.confirmed_at = now_cn()
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.delete("/{loan_id}")
def delete_loan(loan_id: int, db: DbSession, user: ViewerUser):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以删除陪玩借款")
    record = db.get(CompanionLoan, loan_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}
