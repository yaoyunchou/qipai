"""执行 sql/supabase/04-expense-module.sql。用法: python -m scripts.apply_expense_schema"""
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = ROOT.parent.parent / "sql" / "supabase" / "04-expense-module.sql"


def _resolve_database_url() -> str:
    load_dotenv(ROOT / ".env")
    from app.config import settings

    if not settings.database_url:
        print("错误：请在 backend/.env 中配置 DATABASE_URL", file=sys.stderr)
        sys.exit(1)
    return settings.database_url


def _to_psycopg2_dsn(sqlalchemy_url: str, ssl_mode: str) -> str:
    url = make_url(sqlalchemy_url)
    drivername = url.drivername.split("+", 1)[0]
    if drivername != "postgresql":
        print(f"错误：仅支持 PostgreSQL，当前为 {url.drivername}", file=sys.stderr)
        sys.exit(1)
    parts = [
        f"host={url.host}",
        f"port={url.port or 5432}",
        f"dbname={url.database or 'postgres'}",
        f"user={url.username}",
        f"password={url.password}",
    ]
    if ssl_mode:
        parts.append(f"sslmode={ssl_mode}")
    return " ".join(parts)


def main() -> None:
    if not SQL_FILE.is_file():
        print(f"错误：找不到 SQL 文件 {SQL_FILE}", file=sys.stderr)
        sys.exit(1)

    load_dotenv(ROOT / ".env")
    from app.config import settings

    dsn = _to_psycopg2_dsn(_resolve_database_url(), settings.database_ssl_mode)
    sql = SQL_FILE.read_text(encoding="utf-8")

    print(f"执行 {SQL_FILE.name} ...")
    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.close()
    print("报销模块表结构已创建。")


if __name__ == "__main__":
    main()
