from datetime import datetime

from typing import Annotated



from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select

from sqlalchemy.orm import Session



from app.core.deps import CurrentUser, DbSession, require_roles

from app.models import BizOrder, OrderStatus, RoomTable, SysStoreConfig, SysUser, UserRole

from app.schemas.table import TableBoardItem, TableCreate, TableUpdate

from app.services.billing import calc_timing_bill



router = APIRouter(prefix="/tables", tags=["tables"])

AdminUser = Annotated[SysUser, Depends(require_roles(UserRole.ADMIN))]





def _store_cfg(db: Session) -> SysStoreConfig | None:

    return db.get(SysStoreConfig, 1)





def _to_board_item(t: RoomTable, order: BizOrder | None, cfg: SysStoreConfig | None) -> TableBoardItem:

    now = datetime.now()

    enable_timing = bool(cfg and cfg.enable_timing)

    unit_price = cfg.base_price if cfg else None

    billing_unit_minutes = cfg.billing_unit_minutes if cfg else 60

    actual_price = order.actual_price if order else None

    billing_minutes = order.billing_minutes if order else None

    opened_at = order.opened_at if order else None



    if order and enable_timing and cfg and opened_at:

        actual_price, billing_minutes = calc_timing_bill(

            opened_at,

            now,

            cfg.base_price,

            cfg.billing_unit_minutes,

            cfg.min_billing_units,

        )



    return TableBoardItem(

        id=t.id,

        name=t.name,

        sort_order=t.sort_order,

        is_enabled=t.is_enabled,

        status="OCCUPIED" if order else "IDLE",

        open_order_id=order.id if order else None,

        open_order_no=order.order_no if order else None,

        base_price=order.base_price if order else None,

        actual_price=actual_price,

        remark=order.remark if order else None,

        opened_at=opened_at,

        billing_minutes=billing_minutes,

        enable_timing=enable_timing,

        billing_unit_minutes=billing_unit_minutes,

        unit_price=unit_price,

    )





def _board_items(db: Session) -> list[TableBoardItem]:

    cfg = _store_cfg(db)

    tables = db.scalars(

        select(RoomTable).where(RoomTable.is_enabled.is_(True)).order_by(RoomTable.sort_order)

    ).all()

    open_orders = {

        o.table_id: o

        for o in db.scalars(select(BizOrder).where(BizOrder.status == OrderStatus.OPEN)).all()

    }

    return [_to_board_item(t, open_orders.get(t.id), cfg) for t in tables]





@router.get("/board", response_model=list[TableBoardItem])

def board(db: DbSession, user: CurrentUser):

    if user.role == UserRole.SHAREHOLDER:

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="股东无开单权限")

    return _board_items(db)





@router.get("", response_model=list[TableBoardItem])

def list_all(db: DbSession, _: AdminUser):

    cfg = _store_cfg(db)

    tables = db.scalars(select(RoomTable).order_by(RoomTable.sort_order)).all()

    open_orders = {

        o.table_id: o

        for o in db.scalars(select(BizOrder).where(BizOrder.status == OrderStatus.OPEN)).all()

    }

    return [_to_board_item(t, open_orders.get(t.id), cfg) for t in tables]





@router.post("", status_code=status.HTTP_201_CREATED)

def create(body: TableCreate, db: DbSession, _: AdminUser):

    if db.scalar(select(RoomTable).where(RoomTable.name == body.name)):

        raise HTTPException(status_code=400, detail="桌台名称已存在")

    t = RoomTable(name=body.name, sort_order=body.sort_order, is_enabled=body.is_enabled)

    db.add(t)

    db.commit()

    db.refresh(t)

    return {"id": t.id}





@router.patch("/{table_id}")

def update(

    table_id: int, body: TableUpdate, db: DbSession, _: AdminUser

):

    t = db.get(RoomTable, table_id)

    if not t:

        raise HTTPException(status_code=404, detail="桌台不存在")

    if body.name is not None:

        t.name = body.name

    if body.sort_order is not None:

        t.sort_order = body.sort_order

    if body.is_enabled is not None:

        t.is_enabled = body.is_enabled

    db.commit()

    return {"ok": True}





@router.delete("/{table_id}")

def delete(table_id: int, db: DbSession, _: AdminUser):

    t = db.get(RoomTable, table_id)

    if not t:

        raise HTTPException(status_code=404, detail="桌台不存在")

    open_o = db.scalar(

        select(BizOrder).where(

            BizOrder.table_id == table_id, BizOrder.status == OrderStatus.OPEN

        )

    )

    if open_o:

        raise HTTPException(status_code=400, detail="该桌台有未结订单，无法删除")

    db.delete(t)

    db.commit()

    return {"ok": True}

