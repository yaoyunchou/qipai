"""陪玩记账（独立模块）。

场景：客人不够人时安排陪玩，陪玩相关的收支单独记账，不混入台位订单与报销。
每笔记到一名陪玩员工。收银员 / 经理 / 超管可录入；股东可查看。
普通陪玩账号不能查看本模块。删除仅超管可操作。
金额语义：正数为赢（进账），负数为输（支出）。发生时间精确到小时。
"""
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.timezone import now_cn
from app.models import PlayCompanionRecord, RoomTable, SysUser, UserRole
from app.schemas.play_companion import (
    CompanionStaffOut,
    PlayCompanionCreate,
    PlayCompanionOut,
    PlayCompanionSummaryOut,
    PlayCompanionUpdate,
)

router = APIRouter(prefix="/play-companion", tags=["play-companion"])

EditorUser = Annotated[
    SysUser, Depends(require_roles(UserRole.CASHIER, UserRole.MANAGER, UserRole.ADMIN))
]

LIST_ROLES = (
    UserRole.CASHIER,
    UserRole.MANAGER,
    UserRole.ADMIN,
    UserRole.SHAREHOLDER,
)


def _to_out(record: PlayCompanionRecord, db) -> PlayCompanionOut:
    creator = db.get(SysUser, record.created_by)
    companion = db.get(SysUser, record.companion_user_id) if record.companion_user_id else None
    return PlayCompanionOut(
        id=record.id,
        play_date=record.play_date,
        companion_user_id=record.companion_user_id,
        companion_username=companion.username if companion else None,
        companion_name=companion.display_name if companion else None,
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


def _require_companion(db, companion_user_id: int) -> SysUser:
    companion = db.get(SysUser, companion_user_id)
    if not companion or companion.role != UserRole.COMPANION:
        raise HTTPException(status_code=400, detail="请选择陪玩员工")
    if not companion.is_enabled:
        raise HTTPException(status_code=400, detail="该陪玩已停用，不能再记新账")
    return companion


def _ensure_editable(record: PlayCompanionRecord, user: SysUser) -> None:
    if user.role == UserRole.ADMIN:
        return
    if record.created_by != user.id:
        raise HTTPException(status_code=403, detail="只能修改自己录入的陪玩记录")


def _apply_filters(q, start: datetime | None, end: datetime | None, companion_user_id: int | None):
    if start:
        q = q.where(PlayCompanionRecord.play_date >= start)
    if end:
        q = q.where(PlayCompanionRecord.play_date <= end)
    if companion_user_id:
        q = q.where(PlayCompanionRecord.companion_user_id == companion_user_id)
    return q


@router.get("/companions", response_model=list[CompanionStaffOut])
def list_companions(db: DbSession, user: CurrentUser):
    """可选陪玩。工号是用户名，别名是显示名。普通陪玩不能查看这份名单。"""
    if user.role not in LIST_ROLES:
        raise HTTPException(status_code=403, detail="无权查看陪玩名单")
    q = (
        select(SysUser)
        .where(SysUser.role == UserRole.COMPANION, SysUser.is_enabled.is_(True))
        .order_by(SysUser.username)
    )
    rows = db.scalars(q).all()
    return [
        CompanionStaffOut(
            id=row.id,
            username=row.username,
            display_name=row.display_name,
            is_enabled=row.is_enabled,
        )
        for row in rows
    ]


@router.get("/summary", response_model=PlayCompanionSummaryOut)
def summary(
    db: DbSession,
    user: CurrentUser,
    start: datetime | None = Query(None, description="起始时间"),
    end: datetime | None = Query(None, description="结束时间"),
    companion_user_id: int | None = Query(None, description="陪玩用户 id，空则按当前可见范围合计"),
):
    """陪玩汇总。按所选陪玩合计，不选则合计全部。"""
    if user.role not in LIST_ROLES:
        raise HTTPException(status_code=403, detail="无权查看陪玩汇总")
    scoped = companion_user_id
    amount = PlayCompanionRecord.amount
    q = select(
        func.count(PlayCompanionRecord.id),
        func.coalesce(func.sum(case((amount > 0, amount), else_=0)), 0),
        func.coalesce(func.sum(case((amount < 0, -amount), else_=0)), 0),
        func.coalesce(func.sum(amount), 0),
        func.coalesce(func.sum(PlayCompanionRecord.duration_hours), 0),
    )
    q = _apply_filters(q, start, end, scoped)
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
    start: datetime | None = None,
    end: datetime | None = None,
    companion_user_id: int | None = None,
    limit: int = Query(200, le=500),
):
    if user.role not in LIST_ROLES:
        raise HTTPException(status_code=403, detail="无权查看陪玩明细")
    scoped = companion_user_id
    q = (
        select(PlayCompanionRecord)
        .order_by(PlayCompanionRecord.play_date.desc(), PlayCompanionRecord.id.desc())
        .limit(limit)
    )
    q = _apply_filters(q, start, end, scoped)
    records = db.scalars(q).all()
    return [_to_out(r, db) for r in records]


@router.post("", response_model=PlayCompanionOut, status_code=status.HTTP_201_CREATED)
def create_record(body: PlayCompanionCreate, db: DbSession, user: EditorUser):
    _require_companion(db, body.companion_user_id)
    table_id, table_name = _resolve_table(db, body.table_id)
    record = PlayCompanionRecord(
        play_date=body.play_date,
        companion_user_id=body.companion_user_id,
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
    _require_companion(db, body.companion_user_id)

    table_id, table_name = _resolve_table(db, body.table_id)
    record.play_date = body.play_date
    record.companion_user_id = body.companion_user_id
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
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以删除陪玩记录")
    record = db.get(PlayCompanionRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}
