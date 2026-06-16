"""设置或重置 admin 密码。用法: python -m scripts.init_admin [密码]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import SysStoreConfig, SysUser, UserRole


def main() -> None:
    password = sys.argv[1] if len(sys.argv) > 1 else "admin123"
    db = SessionLocal()
    try:
        user = db.scalar(select(SysUser).where(SysUser.username == "admin"))
        if user:
            user.password_hash = hash_password(password)
            user.is_enabled = True
            user.role = UserRole.ADMIN
            print(f"已更新 admin 密码")
        else:
            db.add(
                SysUser(
                    username="admin",
                    password_hash=hash_password(password),
                    display_name="超级管理员",
                    role=UserRole.ADMIN,
                    is_enabled=True,
                )
            )
            print("已创建 admin 账号")
        if not db.get(SysStoreConfig, 1):
            db.add(SysStoreConfig(id=1, base_price=100))
            print("已写入默认门店配置")
        db.commit()
        print(f"登录: admin / {password}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
