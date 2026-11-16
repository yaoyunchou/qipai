from datetime import date, datetime, timedelta
from decimal import Decimal

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.timezone import now_cn
from app.models import BizOrder, ExpenseClaim, LoanRecord, OrderStatus, PlayCompanionRecord, PriceChangeLog, RoomTable, SysStoreConfig, SysUser, UserRole
from app.schemas.order import OrderCloseRequest, OrderOpenRequest, OrderOut, OperationsResetOut
from app.services.billing import calc_timing_bill
from app.services.expense_storage import clear_expense_uploads
from app.services.order_no import generate_order_no

router = APIRouter(prefix="/orders", tags=["orders"])
AdminUser = Annotated[SysUser, Depends(require_roles(UserRole.ADMIN))]


def _to_out(order: BizOrder, db) -> OrderOut:
    table = db.get(RoomTable, order.table_id)
    opener = db.get(SysUser, order.opened_by)
    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        table_id=order.table_id,
        table_name=table.name if table else None,
        base_price=order.base_price,
        actual_price=order.actual_price,
        billing_minutes=order.billing_minutes,
        status=order.status,
        remark=order.remark,
        opened_by=order.opened_by,
        opened_by_name=opener.display_name if opener else None,
        opened_at=order.opened_at,
        closed_by=order.closed_by,
        closed_at=order.closed_at,
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: DbSession,
    user: CurrentUser,
    status_filter: OrderStatus | None = Query(None, alias="status"),
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(50, le=500),
):
    q = select(BizOrder).order_by(BizOrder.opened_at.desc()).limit(limit)
    if status_filter:
        q = q.where(BizOrder.status == status_filter)
    if start:
        q = q.where(BizOrder.opened_at >= datetime.combine(start, datetime.min.time()))
    if end:
        q = q.where(BizOrder.opened_at < datetime.combine(end + timedelta(days=1), datetime.min.time()))
    if user.role in (UserRole.CASHIER, UserRole.SHAREHOLDER):
        q = q.where(BizOrder.opened_by == user.id)
    orders = db.scalars(q).all()
    return [_to_out(o, db) for o in orders]


@router.post("/open", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def open_order(body: OrderOpenRequest, db: DbSession, user: CurrentUser):
    table = db.get(RoomTable, body.table_id)
    if not table or not table.is_enabled:
        raise HTTPException(status_code=400, detail="桌台不可用")
    existing = db.scalar(
        select(BizOrder).where(
            BizOrder.table_id == body.table_id, BizOrder.status == OrderStatus.OPEN
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="该桌台已有进行中订单")
    cfg = db.get(SysStoreConfig, 1)
    if not cfg:
        raise HTTPException(status_code=500, detail="门店配置未初始化")
    base = cfg.base_price
    opened_at = body.opened_at if body.opened_at is not None else now_cn()
    if opened_at > now_cn():
        raise HTTPException(status_code=400, detail="开始时间不能晚于当前时间")
    if cfg.enable_timing:
        if body.actual_price is not None:
            raise HTTPException(status_code=400, detail="计时模式下开单不需填写价格，清台时自动结算")
        actual = Decimal("0")
        billing_minutes = None
    else:
        actual = body.actual_price if body.actual_price is not None else base
        billing_minutes = None
        if user.role == UserRole.CASHIER and not cfg.cashier_allow_custom_price:
            if actual != base:
                raise HTTPException(status_code=403, detail="不允许自定义价格")
    order = BizOrder(
        order_no=generate_order_no(),
        table_id=body.table_id,
        base_price=base,
        actual_price=actual,
        billing_minutes=billing_minutes,
        status=OrderStatus.OPEN,
        remark=body.remark,
        opened_by=user.id,
        opened_at=opened_at,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _to_out(order, db)


@router.post("/{order_id}/close", response_model=OrderOut)
def close_order(
    order_id: int,
    body: OrderCloseRequest,
    db: DbSession,
    user: CurrentUser,
):
    order = db.get(BizOrder, order_id)
    if not order or order.status != OrderStatus.OPEN:
        raise HTTPException(status_code=404, detail="订单不存在或已归档")
    cfg = db.get(SysStoreConfig, 1)
    if not cfg:
        raise HTTPException(status_code=500, detail="门店配置未初始化")
    closed_at = now_cn()
    if cfg.enable_timing:
        auto_price, billing_minutes = calc_timing_bill(
            order.opened_at,
            closed_at,
            order.base_price,
            cfg.billing_unit_minutes,
            cfg.min_billing_units,
        )
        if body.actual_price is not None:
            if user.role == UserRole.CASHIER and not cfg.cashier_allow_custom_price:
                raise HTTPException(status_code=403, detail="不允许自定义价格")
            order.actual_price = body.actual_price
            order.billing_minutes = billing_minutes
        else:
            order.actual_price = auto_price
            order.billing_minutes = billing_minutes
    elif body.actual_price is not None:
        if user.role == UserRole.CASHIER and not cfg.cashier_allow_custom_price:
            raise HTTPException(status_code=403, detail="不允许自定义价格")
        order.actual_price = body.actual_price
    order.status = OrderStatus.CLOSED
    order.closed_by = user.id
    order.closed_at = closed_at
    db.commit()
    db.refresh(order)
    return _to_out(order, db)


@router.post("/reset-operations", response_model=OperationsResetOut)
def reset_operations(db: DbSession, user: AdminUser):
    """清除全部运营数据：订单、报销单及附件、陪玩记录、借钱记录、基准价变更记录（仅超管）。"""
    orders_count = db.scalar(select(func.count()).select_from(BizOrder)) or 0
    claims_count = db.scalar(select(func.count()).select_from(ExpenseClaim)) or 0
    logs_count = db.scalar(select(func.count()).select_from(PriceChangeLog)) or 0
    play_count = db.scalar(select(func.count()).select_from(PlayCompanionRecord)) or 0
    loan_count = db.scalar(select(func.count()).select_from(LoanRecord)) or 0

    db.execute(
        text(
            "TRUNCATE expense_claim_approver, expense_claim_attachment, "
            "expense_claim, play_companion_record, loan_record, biz_order, price_change_log "
            "RESTART IDENTITY CASCADE"
        )
    )
    db.commit()
    clear_expense_uploads()

    return OperationsResetOut(
        deleted_orders=orders_count,
        deleted_expense_claims=claims_count,
        deleted_price_logs=logs_count,
        deleted_play_companion=play_count,
        deleted_loan_records=loan_count,
    )
