from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.timezone import now_cn, today_cn
from app.models import BizOrder, OrderStatus, RoomTable, SysStoreConfig, SysUser, UserRole
from app.schemas.report import ReportSummary

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_range(period: str, start: date | None, end: date | None) -> tuple[datetime, datetime, str, str]:
    today = today_cn()
    if period == "day":
        d = start or today
        s = datetime.combine(d, datetime.min.time())
        e = s + timedelta(days=1)
        return s, e, d.isoformat(), d.isoformat()
    if period == "week":
        d = start or today
        s = datetime.combine(d - timedelta(days=d.weekday()), datetime.min.time())
        e = s + timedelta(days=7)
        return s, e, s.date().isoformat(), (e.date() - timedelta(days=1)).isoformat()
    if period == "month":
        d = start or today
        s = datetime.combine(d.replace(day=1), datetime.min.time())
        if d.month == 12:
            e = datetime(d.year + 1, 1, 1)
        else:
            e = datetime(d.year, d.month + 1, 1)
        return s, e, s.date().isoformat(), (e.date() - timedelta(days=1)).isoformat()
    raise HTTPException(status_code=400, detail="period 须为 day|week|month")


def _apply_report_limit(user: CurrentUser, db, start: datetime) -> None:
    cfg = db.get(SysStoreConfig, 1)
    if not cfg:
        return
    if user.role == UserRole.CASHIER and cfg.cashier_report_months:
        earliest = now_cn() - timedelta(days=cfg.cashier_report_months * 31)
        if start < earliest:
            raise HTTPException(status_code=403, detail="超出可查报表时间范围")
    if user.role == UserRole.ADMIN and cfg.admin_report_days:
        earliest = now_cn() - timedelta(days=cfg.admin_report_days)
        if start < earliest:
            raise HTTPException(status_code=403, detail="超出可查报表时间范围")


@router.get("/summary", response_model=ReportSummary)
def summary(
    db: DbSession,
    user: CurrentUser,
    period: str = Query("day", pattern="^(day|week|month)$"),
    start: date | None = None,
    end: date | None = None,
):
    s, e, start_str, end_str = _parse_range(period, start, end)
    _apply_report_limit(user, db, s)
    q = select(
        func.count(BizOrder.id),
        func.coalesce(func.sum(BizOrder.base_price), 0),
        func.coalesce(func.sum(BizOrder.actual_price), 0),
    ).where(
        BizOrder.status == OrderStatus.CLOSED,
        BizOrder.closed_at >= s,
        BizOrder.closed_at < e,
    )
    if user.role == UserRole.CASHIER:
        q = q.where(BizOrder.opened_by == user.id)
    row = db.execute(q).one()
    return ReportSummary(
        period=period,
        start_date=start_str,
        end_date=end_str,
        order_count=int(row[0] or 0),
        base_price_total=Decimal(str(row[1])),
        actual_price_total=Decimal(str(row[2])),
    )


def _can_export(user: CurrentUser, cfg: SysStoreConfig | None) -> bool:
    if user.role in (UserRole.MANAGER, UserRole.SHAREHOLDER, UserRole.ADMIN):
        return True
    if user.role == UserRole.CASHIER:
        return bool(cfg and cfg.cashier_allow_export)
    return False


def _query_orders(db, user: CurrentUser, s: datetime, e: datetime):
    q = (
        select(BizOrder, RoomTable.name, SysUser.display_name)
        .join(RoomTable, BizOrder.table_id == RoomTable.id)
        .join(SysUser, BizOrder.opened_by == SysUser.id)
        .where(
            BizOrder.status == OrderStatus.CLOSED,
            BizOrder.closed_at >= s,
            BizOrder.closed_at < e,
        )
        .order_by(BizOrder.closed_at.desc())
    )
    if user.role == UserRole.CASHIER:
        q = q.where(BizOrder.opened_by == user.id)
    return db.execute(q).all()


@router.get("/export")
def export_excel(
    db: DbSession,
    user: CurrentUser,
    period: str = Query("day", pattern="^(day|week|month)$"),
    start: date | None = None,
    end: date | None = None,
):
    cfg = db.get(SysStoreConfig, 1)
    if not _can_export(user, cfg):
        raise HTTPException(status_code=403, detail="无报表导出权限")
    s, e, start_str, end_str = _parse_range(period, start, end)
    _apply_report_limit(user, db, s)

    q = select(
        func.count(BizOrder.id),
        func.coalesce(func.sum(BizOrder.base_price), 0),
        func.coalesce(func.sum(BizOrder.actual_price), 0),
    ).where(
        BizOrder.status == OrderStatus.CLOSED,
        BizOrder.closed_at >= s,
        BizOrder.closed_at < e,
    )
    if user.role == UserRole.CASHIER:
        q = q.where(BizOrder.opened_by == user.id)
    row = db.execute(q).one()
    order_count = int(row[0] or 0)
    base_total = Decimal(str(row[1]))
    actual_total = Decimal(str(row[2]))

    wb = Workbook()
    ws_sum = wb.active
    ws_sum.title = "汇总"
    ws_sum.append(["统计周期", f"{start_str} ~ {end_str}"])
    ws_sum.append(["报表类型", {"day": "日报", "week": "周报", "month": "月报"}[period]])
    ws_sum.append(["开单量", order_count])
    ws_sum.append(["原价总营收", float(base_total)])
    ws_sum.append(["实收总营收", float(actual_total)])

    if user.role != UserRole.SHAREHOLDER:
        ws_detail = wb.create_sheet("订单明细")
        ws_detail.append(
            ["单号", "台位", "原价", "实收", "开单人", "开单时间", "清台时间", "备注"]
        )
        for order, table_name, opener_name in _query_orders(db, user, s, e):
            ws_detail.append(
                [
                    order.order_no,
                    table_name,
                    float(order.base_price),
                    float(order.actual_price),
                    opener_name,
                    order.opened_at.strftime("%Y-%m-%d %H:%M:%S") if order.opened_at else "",
                    order.closed_at.strftime("%Y-%m-%d %H:%M:%S") if order.closed_at else "",
                    order.remark or "",
                ]
            )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"report_{period}_{start_str}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
