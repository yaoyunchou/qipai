"""将 expense_claim_attachment.data_base64 导出为磁盘文件并写入 file_path。

用法:
  python -m scripts.apply_expense_attachment_file   # 先加 file_path 列
  python -m scripts.migrate_expense_attachments       # 再迁移数据
"""
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url

ROOT = Path(__file__).resolve().parents[1]


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


def _column_exists(cur, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'expense_claim_attachment'
          AND column_name = %s
        """,
        (column,),
    )
    return cur.fetchone() is not None


def main() -> None:
    load_dotenv(ROOT / ".env")
    from app.config import settings
    from app.services.expense_storage import save_attachment

    dsn = _to_psycopg2_dsn(_resolve_database_url(), settings.database_ssl_mode)
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            if not _column_exists(cur, "file_path"):
                print("错误：缺少 file_path 列，请先运行 python -m scripts.apply_expense_attachment_file")
                sys.exit(1)

            has_base64 = _column_exists(cur, "data_base64")
            if not has_base64:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM expense_claim_attachment
                    WHERE file_path IS NULL OR file_path = ''
                    """
                )
                pending = cur.fetchone()[0]
                if pending:
                    print(f"警告：仍有 {pending} 条附件缺少 file_path，但 data_base64 列已不存在。")
                else:
                    print("无需迁移：data_base64 列已移除且 file_path 已就绪。")
                return

            cur.execute(
                """
                SELECT id, claim_id, filename, content_type, data_base64
                FROM expense_claim_attachment
                WHERE file_path IS NULL OR file_path = ''
                ORDER BY id
                """
            )
            rows = cur.fetchall()
            if not rows:
                print("没有待迁移的 Base64 附件。")
            else:
                print(f"迁移 {len(rows)} 个附件到 {settings.upload_dir} ...")
                for att_id, claim_id, filename, content_type, data_base64 in rows:
                    file_path = save_attachment(claim_id, filename, content_type, data_base64)
                    cur.execute(
                        "UPDATE expense_claim_attachment SET file_path = %s WHERE id = %s",
                        (file_path, att_id),
                    )
                    print(f"  #{att_id} -> {file_path}")
                conn.commit()

            cur.execute(
                """
                SELECT COUNT(*) FROM expense_claim_attachment
                WHERE file_path IS NULL OR file_path = ''
                """
            )
            if cur.fetchone()[0] == 0:
                print("删除 data_base64 列并设置 file_path NOT NULL ...")
                conn.autocommit = True
                cur.execute("ALTER TABLE expense_claim_attachment DROP COLUMN data_base64")
                cur.execute(
                    "ALTER TABLE expense_claim_attachment ALTER COLUMN file_path SET NOT NULL"
                )
                print("迁移完成。")
            else:
                print("仍有附件未迁移，未删除 data_base64 列。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
