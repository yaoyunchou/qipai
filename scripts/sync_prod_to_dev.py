#!/usr/bin/env python3
"""将生产 PostgreSQL + 报销附件同步到 backend/.env 指向的库（含 Supabase）。

用法:
  python scripts/sync_prod_to_dev.py --yes

依赖（backend 虚拟环境已具备 psycopg2）:
  pip install paramiko python-dotenv
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import paramiko
import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "code" / "backend"
SYNC_DIR = BACKEND / ".sync"
UPLOADS_LOCAL = BACKEND / "uploads"

HOST = os.environ.get("QIPAI_SSH_HOST", "1.12.219.199")
SSH_USER = os.environ.get("QIPAI_SSH_USER", "root")
SSH_PASSWORD = os.environ.get("QIPAI_SSH_PASSWORD", "Jxfg357159..")
REMOTE_BACKEND = "/www/server/qipai/code/backend"
REMOTE_UPLOADS = f"{REMOTE_BACKEND}/uploads"


def _parse_database_url(sqlalchemy_url: str) -> dict[str, str | int]:
    raw = sqlalchemy_url.replace("postgresql+psycopg2://", "postgresql://").replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    parsed = urlparse(raw)
    return {
        "host": parsed.hostname or "localhost",
        "port": int(parsed.port or 5432),
        "database": (parsed.path or "/postgres").lstrip("/") or "postgres",
        "user": unquote(parsed.username or "postgres"),
        "password": unquote(parsed.password or ""),
    }


def _load_local_db_config() -> tuple[str, str]:
    load_dotenv(BACKEND / ".env")
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("请在 code/backend/.env 配置 DATABASE_URL")
    ssl_mode = os.environ.get("DATABASE_SSL_MODE", "require").strip()
    return database_url, ssl_mode


def _connect(db: dict[str, str | int], ssl_mode: str):
    host = str(db["host"])
    port = int(db["port"])
    if "pooler.supabase.com" in host and port == 6543:
        print("    提示: pooler 6543 不支持 DDL，自动改用 5432 会话模式")
        port = 5432
    kwargs = {
        "host": host,
        "port": port,
        "dbname": db["database"],
        "user": db["user"],
        "password": db["password"],
        "connect_timeout": 30,
    }
    if ssl_mode:
        kwargs["sslmode"] = ssl_mode
    return psycopg2.connect(**kwargs)


def _run_ssh(ssh: paramiko.SSHClient, cmd: str, timeout: int = 600) -> int:
    print(f"\n>>> {cmd[:200]}{'...' if len(cmd) > 200 else ''}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    return code


def _remote_pg_dump_sql(ssh: paramiko.SSHClient, remote_sql: str) -> None:
    script = f"""bash -lc '
set -e
cd {REMOTE_BACKEND}
PASS=$(python3 - <<PY
import re
from pathlib import Path
text = Path(".env").read_text(encoding="utf-8")
m = re.search(r"DATABASE_URL=(.+)", text)
line = m.group(1).strip()
m2 = re.search(r"://([^:]+):([^@]+)@", line)
print(m2.group(2) if m2 else "")
PY
)
export PGPASSWORD="$PASS"
pg_dump -h 127.0.0.1 -U qipai -d qipai -n public --inserts --no-owner --no-acl -F p -f {remote_sql}
ls -lh {remote_sql}
'"""
    if _run_ssh(ssh, script, timeout=600) != 0:
        raise SystemExit("生产库 pg_dump 失败")


def _split_sql(sql: str) -> list[str]:
    """按语句拆分 pg_dump plain SQL，正确处理 $$ 函数体。"""
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    dollar_delim: str | None = None
    i = 0
    n = len(sql)

    while i < n:
        if dollar_delim:
            if sql.startswith(dollar_delim, i):
                current.append(dollar_delim)
                i += len(dollar_delim)
                dollar_delim = None
                continue
            current.append(sql[i])
            i += 1
            continue

        if in_single:
            current.append(sql[i])
            if sql[i] == "'":
                if i + 1 < n and sql[i + 1] == "'":
                    current.append("'")
                    i += 2
                    continue
                in_single = False
            i += 1
            continue

        if in_double:
            current.append(sql[i])
            if sql[i] == '"':
                in_double = False
            i += 1
            continue

        if sql[i] == "'":
            in_single = True
            current.append(sql[i])
            i += 1
            continue
        if sql[i] == '"':
            in_double = True
            current.append(sql[i])
            i += 1
            continue
        if sql[i] == "$":
            m = re.match(r"\$[^$]*\$", sql[i:])
            if m:
                dollar_delim = m.group(0)
                current.append(dollar_delim)
                i += len(dollar_delim)
                continue

        if sql[i] == ";":
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        if sql[i:i + 2] == "--":
            end = sql.find("\n", i)
            if end == -1:
                current.append(sql[i:])
                break
            current.append(sql[i : end + 1])
            i = end + 1
            continue

        current.append(sql[i])
        i += 1

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _stmt_body(stmt: str) -> str:
    lines = []
    for line in stmt.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _should_skip_restore_stmt(stmt: str) -> bool:
    s = _stmt_body(stmt)
    if not s:
        return True
    upper = s.upper()
    if upper.startswith("\\"):
        return True
    if upper.startswith("DROP "):
        return True
    if upper.startswith("ALTER TABLE") and " DROP " in upper:
        return True
    if upper.startswith("ALTER TABLE") and "ALTER COLUMN" in upper and " DROP " in upper:
        return True
    if upper.startswith("CREATE SCHEMA"):
        return True
    if upper.startswith("COMMENT ON SCHEMA"):
        return True
    if upper.startswith("SET ") or upper.startswith("SELECT PG_CATALOG."):
        return True
    return False


def _apply_local_migrations(database_url: str, ssl_mode: str) -> None:
    """同步生产 dump 后补齐增量迁移（生产库可能尚未执行最新脚本）。"""
    migration_dir = ROOT / "sql" / "supabase"
    incremental = (
        "05-expense-category.sql",
        "06-expense-attachment-file.sql",
        "07-expense-voided.sql",
    )
    files = [migration_dir / name for name in incremental if (migration_dir / name).is_file()]
    if not files:
        return
    db = _parse_database_url(database_url)
    conn = _connect(db, ssl_mode)
    conn.autocommit = True
    print("\n>>> 补齐增量 schema 迁移 ...")
    try:
        with conn.cursor() as cur:
            for path in files:
                print(f"    {path.name}")
                cur.execute(path.read_text(encoding="utf-8"))
    finally:
        conn.close()


def _local_restore_sql(sql_file: Path, database_url: str, ssl_mode: str) -> None:
    db = _parse_database_url(database_url)
    print(f"\n>>> 写入 Supabase/本地库 {db['host']}:{db['port']}/{db['database']} ...")
    print("    （先 DROP SCHEMA public CASCADE，再导入生产数据）")

    sql = sql_file.read_text(encoding="utf-8", errors="replace")

    conn = _connect(db, ssl_mode)
    conn.autocommit = True
    ok = 0
    try:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
            cur.execute("CREATE SCHEMA public")
            cur.execute("GRANT ALL ON SCHEMA public TO postgres")
            cur.execute("GRANT ALL ON SCHEMA public TO public")
            for stmt in _split_sql(sql):
                if _should_skip_restore_stmt(stmt):
                    continue
                cur.execute(_stmt_body(stmt))
                ok += 1
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM expense_claim")
            count = cur.fetchone()[0]
        print(f"恢复完成: 导入 {ok} 条 SQL，expense_claim={count} 条")
    finally:
        conn.close()
    _apply_local_migrations(database_url, ssl_mode)


def _download_uploads(sftp: paramiko.SFTPClient, remote: str, local: Path) -> None:
    import stat

    local.mkdir(parents=True, exist_ok=True)

    def _is_dir(attr) -> bool:
        return stat.S_ISDIR(attr.st_mode)

    def _walk(rdir: str, ldir: Path) -> None:
        for entry in sftp.listdir_attr(rdir):
            name = entry.filename
            if name.startswith("."):
                continue
            rpath = f"{rdir}/{name}"
            lpath = ldir / name
            if _is_dir(entry):
                lpath.mkdir(parents=True, exist_ok=True)
                _walk(rpath, lpath)
            else:
                print(f"  {lpath.relative_to(local)}")
                sftp.get(rpath, str(lpath))

    try:
        sftp.listdir(remote)
    except FileNotFoundError:
        print(f"远程无 uploads: {remote}，跳过")
        return

    print(f"\n下载附件 -> {local}")
    _walk(remote, local)


def main() -> int:
    parser = argparse.ArgumentParser(description="生产数据同步到 Supabase/本地开发库")
    parser.add_argument("--yes", action="store_true", help="跳过确认")
    parser.add_argument("--skip-uploads", action="store_true")
    parser.add_argument("--skip-restore", action="store_true")
    parser.add_argument("--restore-only", metavar="SQL", help="仅恢复已有 .sql 文件")
    args = parser.parse_args()

    database_url, ssl_mode = _load_local_db_config()
    db = _parse_database_url(database_url)

    print("=" * 60)
    print("生产 -> Supabase/本地  数据同步")
    print(f"  生产: {SSH_USER}@{HOST}")
    print(f"  目标: {db['host']}:{db['port']}/{db['database']}")
    print("=" * 60)

    if not args.yes and not args.restore_only:
        ans = input("将覆盖目标库 public 数据，确认？(yes/no): ").strip().lower()
        if ans not in ("yes", "y"):
            print("已取消")
            return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    local_sql = SYNC_DIR / f"prod_qipai_{ts}.sql"

    if args.restore_only:
        local_sql = Path(args.restore_only)
        if not local_sql.is_file():
            raise SystemExit(f"找不到: {local_sql}")
        _local_restore_sql(local_sql, database_url, ssl_mode)
        return 0

    remote_sql = f"/tmp/qipai_sync_{ts}.sql"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"\n连接 {SSH_USER}@{HOST} ...")
    ssh.connect(HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=30)

    try:
        _remote_pg_dump_sql(ssh, remote_sql)
        print(f"\n下载 SQL -> {local_sql}")
        sftp = ssh.open_sftp()
        sftp.get(remote_sql, str(local_sql))
        _run_ssh(ssh, f"rm -f {remote_sql}")
        if not args.skip_uploads:
            _download_uploads(sftp, REMOTE_UPLOADS, UPLOADS_LOCAL)
        sftp.close()
    finally:
        ssh.close()

    if not args.skip_restore:
        _local_restore_sql(local_sql, database_url, ssl_mode)

    print("\n全部完成。")
    print(f"  SQL 备份: {local_sql}")
    print("  建议 .env: UPLOAD_DIR=uploads  UPLOAD_URL_PREFIX=/uploads")
    print("  启动: cd code && .\\start.ps1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
