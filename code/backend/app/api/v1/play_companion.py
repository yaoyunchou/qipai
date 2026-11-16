"""陪玩记账（独立模块）。

场景：客人不够人时安排陪玩，陪玩相关的收支单独记账，不混入台位订单与报销。
权限：收银员 / 经理 / 超管可录入与查看明细；股东只能看汇总。
金额语义：正数为赢（进账），负数为输（支出）。
"""
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.timezone import now_cn
from app.models import PlayCompanionRecord, RoomTable, SysUser, UserRole
from app.schemas.play_companion import (
    PlayCompanionCreate,
    PlayCompanionOut,
    PlayCompanionSummaryOut,
    PlayCompanionUpdate,
)

router = APIRouter(prefix="/play-companion", tags=["play-companion"])

EditorUser = Annotated[
    SysUser, Depends(require_roles(UserRole.CASHIER, UserRole.MANAGER, UserRole.ADMIN))
]

VIEWER_ROLES = (UserRole.CASHIER, UserRole.MANAGER, UserRole.ADMIN)


def _to_out(record: PlayCompanionRecord, db) -> PlayCompanionOut:
    creator = db.get(SysUser, record.created_by)
    return PlayCompanionOut(
        id=record.id,
        play_date=record.play_date,
        table_id=record.table_id,
        table_name=record.table_name,
        duration_hours=record.duration_hours,
        amount=record.amount,
        remark=record.remark,
        created_by=record.created_by,
        created_by_name=creator.display_name if creator else None,
        created_at=record.created_at,
    )


def _resolve_table(db, table_id: int | None) -> tuple[int | None, str]:
    """校验台位并保存名称快照，便于台位被删除后列表仍可读。"""
    if table_id is None:
        return None, ""
    table = db.get(RoomTable, table_id)
    if not table:
        raise HTTPException(status_code=400, detail="台位不存在")
    return table.id, table.name


def _ensure_editable(record: PlayCompanionRecord, user: SysUser) -> None:
    if user.role == UserRole.ADMIN:
        return
    if record.created_by != user.id:
        raise HTTPException(status_code=403, detail="只能修改自己录入的陪玩记录")


@router.get("/summary", response_model=PlayCompanionSummaryOut)
def summary(
    db: DbSession,
    user: CurrentUser,
    start: date | None = Query(None, description="起始日期 YYYY-MM-DD"),
    end: date | None = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """陪玩汇总（股东可用）。赢 / 输分开合计，并给出净额。"""
    amount = PlayCompanionRecord.amount
    q = select(
        func.count(PlayCompanionRecord.id),
        func.coalesce(func.sum(case((amount > 0, amount), else_=0)), 0),
        func.coalesce(func.sum(case((amount < 0, -amount), else_=0)), 0),
        func.coalesce(func.sum(amount), 0),
        func.coalesce(func.sum(PlayCompanionRecord.duration_hours), 0),
    )
    if start:
        q = q.where(PlayCompanionRecord.play_date >= start)
    if end:
        q = q.where(PlayCompanionRecord.play_date <= end)
    row = db.execute(q).one()
    return PlayCompanionSummaryOut(
        record_count=int(row[0] or 0),
        win_total=Decimal(str(row[1])),
        lose_total=Decimal(str(row[2])),
        net_total=Decimal(str(row[3])),
        duration_total=Decimal(str(row[4])),
    )


@router.get("", response_model=list[PlayCompanionOut])
def list_records(
    db: DbSession,
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(200, le=500),
):
    if user.role not in VIEWER_ROLES:
        raise HTTPException(status_code=403, detail="仅可查看陪玩汇总")

    q = (
        select(PlayCompanionRecord)
        .order_by(PlayCompanionRecord.play_date.desc(), PlayCompanionRecord.id.desc())
        .limit(limit)
    )
    if start:
        q = q.where(PlayCompanionRecord.play_date >= start)
    if end:
        q = q.where(PlayCompanionRecord.play_date <= end)
    records = db.scalars(q).all()
    return [_to_out(r, db) for r in records]


@router.post("", response_model=PlayCompanionOut, status_code=status.HTTP_201_CREATED)
def create_record(body: PlayCompanionCreate, db: DbSession, user: EditorUser):
    table_id, table_name = _resolve_table(db, body.table_id)
    record = PlayCompanionRecord(
        play_date=body.play_date,
        table_id=table_id,
        table_name=table_name,
        duration_hours=body.duration_hours,
        amount=body.amount,
        remark=body.remark,
        created_by=user.id,
        created_at=now_cn(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.put("/{record_id}", response_model=PlayCompanionOut)
def update_record(record_id: int, body: PlayCompanionUpdate, db: DbSession, user: EditorUser):
    record = db.get(PlayCompanionRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _ensure_editable(record, user)

    table_id, table_name = _resolve_table(db, body.table_id)
    record.play_date = body.play_date
    record.table_id = table_id
    record.table_name = table_name
    record.duration_hours = body.duration_hours
    record.amount = body.amount
    record.remark = body.remark
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.delete("/{record_id}")
def delete_record(record_id: int, db: DbSession, user: EditorUser):
    record = db.get(PlayCompanionRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _ensure_editable(record, user)
    db.delete(record)
    db.commit()
    return {"ok": True}
