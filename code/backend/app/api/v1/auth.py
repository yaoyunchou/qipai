from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token, verify_password
from app.models import SysUser
from app.schemas.auth import LoginRequest, TokenResponse, UserMe
from app.services.home_path import home_path_for

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession):
    user = db.scalar(select(SysUser).where(SysUser.username == body.username))
    if not user or not user.is_enabled or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(str(user.id), {"role": user.role.value})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserMe)
def me(user: CurrentUser):
    return UserMe(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        home_path=home_path_for(user.role),
    )
