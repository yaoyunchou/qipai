from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.deps import DbSession, require_roles
from app.core.security import hash_password
from app.models import SysUser, UserRole
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
AdminUser = Annotated[SysUser, Depends(require_roles(UserRole.ADMIN))]


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, _: AdminUser):
    users = db.scalars(select(SysUser).order_by(SysUser.id)).all()
    return users


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: DbSession, _: AdminUser):
    if db.scalar(select(SysUser).where(SysUser.username == body.username)):
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = SysUser(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.username,
        role=body.role,
        is_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: DbSession, admin: AdminUser):
    user = db.get(SysUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        user.role = body.role
    if body.is_enabled is not None:
        if user.id == admin.id and not body.is_enabled:
            raise HTTPException(status_code=400, detail="不能禁用当前登录账号")
        user.is_enabled = body.is_enabled
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DbSession, admin: AdminUser):
    user = db.get(SysUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    db.delete(user)
    db.commit()
