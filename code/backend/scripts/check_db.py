"""测试 Supabase 数据库连接。用法: python -m scripts.check_db"""
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    load_dotenv(ROOT / ".env")
    try:
        from app.database import engine
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("数据库连接成功")
        return 0
    except Exception as e:
        print(f"数据库连接失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
