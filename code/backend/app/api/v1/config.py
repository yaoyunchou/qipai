from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models import SysUser
from app.models import PriceChangeLog, SysStoreConfig, UserRole
from app.schemas.config import StoreConfigOut, StoreConfigUpdate

router = APIRouter(prefix="/config", tags=["config"])
AdminUser = Annotated[SysUser, Depends(require_roles(UserRole.ADMIN))]


def _get_config(db) -> SysStoreConfig:
    cfg = db.get(SysStoreConfig, 1)
    if not cfg:
        raise HTTPException(status_code=500, detail="门店配置未初始化，请执行 SQL 初始化")
    return cfg


@router.get("/store", response_model=StoreConfigOut)
def get_store(db: DbSession, _: CurrentUser):
    return _get_config(db)


@router.put("/store", response_model=StoreConfigOut)
def update_store(
    body: StoreConfigUpdate, db: DbSession, user: AdminUser
):
    cfg = _get_config(db)
    if body.base_price is not None and body.base_price != cfg.base_price:
        db.add(
            PriceChangeLog(
                old_price=cfg.base_price,
                new_price=body.base_price,
                changed_by=user.id,
            )
        )
        cfg.base_price = body.base_price
    if body.enable_timing is not None:
        cfg.enable_timing = body.enable_timing
    if body.billing_unit_minutes is not None:
        cfg.billing_unit_minutes = body.billing_unit_minutes
    if body.min_billing_units is not None:
        cfg.min_billing_units = body.min_billing_units
    if body.cashier_allow_custom_price is not None:
        cfg.cashier_allow_custom_price = body.cashier_allow_custom_price
    if body.cashier_allow_export is not None:
        cfg.cashier_allow_export = body.cashier_allow_export
    if body.cashier_report_months is not None:
        cfg.cashier_report_months = body.cashier_report_months
    if body.admin_report_days is not None:
        cfg.admin_report_days = body.admin_report_days
    cfg.updated_by = user.id
    db.commit()
    db.refresh(cfg)
    return cfg
