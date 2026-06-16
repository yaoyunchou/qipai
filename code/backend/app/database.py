import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL 未配置。请在 backend/.env 中设置 Supabase PostgreSQL 连接串，"
        "参考 backend/.env.example"
    )

_is_serverless = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))
_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "connect_args": settings.db_connect_args,
}
if _is_serverless:
    # Vercel Functions 无状态，避免连接池跨请求复用
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_recycle"] = 3600

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
