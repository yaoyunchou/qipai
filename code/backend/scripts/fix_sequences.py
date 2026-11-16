"""修复 INSERT 导入数据后 id 序列落后于 MAX(id) 的问题。用法: python -m scripts.fix_sequences"""
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TABLES_WITH_ID_SERIAL = (
    "sys_user",
    "price_change_log",
    "room_table",
    "biz_order",
    "expense_claim",
    "expense_claim_attachment",
    "expense_claim_approver",
)


def fix_sequences() -> None:
    load_dotenv(ROOT / ".env")
    from app.database import engine

    with engine.connect() as conn:
        for table in TABLES_WITH_ID_SERIAL:
            seq = conn.execute(
                text("SELECT pg_get_serial_sequence(:table, 'id')"),
                {"table": table},
            ).scalar()
            if not seq:
                print(f"  跳过 {table}（无 id 序列）")
                continue
            max_id = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")).scalar() or 0
            next_id = int(max_id) + 1
            conn.execute(text("SELECT setval(:seq, :val, false)"), {"seq": seq, "val": next_id})
            print(f"  {table}: 下一 id = {next_id}")
        conn.commit()


def main() -> int:
    try:
        print("修复 id 序列 ...")
        fix_sequences()
        print("序列已对齐。")
        return 0
    except Exception as e:
        print(f"修复失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
