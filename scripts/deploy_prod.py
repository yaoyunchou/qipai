#!/usr/bin/env python3
"""生产部署：本地备份 → 线上备份 → 上传代码 → 迁移 → 重启 → 发布前端。

用法（项目根目录）:
  # 完整流程（推荐）
  code\\backend\\.venv\\Scripts\\python.exe scripts\\deploy_prod.py --yes

  # 仅本地拉取备份，不部署
  code\\backend\\.venv\\Scripts\\python.exe scripts\\deploy_prod.py --backup-only --yes

  # 跳过本地备份，直接部署（需已构建 frontend/dist）
  code\\backend\\.venv\\Scripts\\python.exe scripts\\deploy_prod.py --skip-local-backup --yes
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
BACKEND_LOCAL = ROOT / "code" / "backend"
FRONTEND_LOCAL = ROOT / "code" / "frontend"
LOCAL_DIST = FRONTEND_LOCAL / "dist"
LOCAL_BACKUPS = ROOT / "backups"
SYNC_SCRIPT = ROOT / "scripts" / "sync_prod_to_dev.py"
PYTHON = BACKEND_LOCAL / ".venv" / "Scripts" / "python.exe"

HOST = os.environ.get("QIPAI_SSH_HOST", "1.12.219.199")
USER = os.environ.get("QIPAI_SSH_USER", "root")
PASSWORD = os.environ.get("QIPAI_SSH_PASSWORD", "Jxfg357159..")
CODE_DIR = "/www/server/qipai"
BACKEND_REMOTE = f"{CODE_DIR}/code/backend"
FRONTEND_REMOTE = "/www/wwwroot/jb.jxfgg.com/qipai"
UPLOADS_REMOTE = f"{BACKEND_REMOTE}/uploads"
SQL_REMOTE = f"{CODE_DIR}/sql/supabase"


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
    print(f"\n>>> {cmd[:300]}{'...' if len(cmd) > 300 else ''}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    return code, out, err


def sftp_upload_dir(sftp: paramiko.SFTPClient, local: Path, remote: str, skip_dirs: set[str] | None = None) -> None:
    skip_dirs = skip_dirs or set()

    def mkdir_p(path: str) -> None:
        parts = path.strip("/").split("/")
        cur = ""
        for p in parts:
            cur += f"/{p}"
            try:
                sftp.mkdir(cur)
            except OSError:
                pass

    mkdir_p(remote)
    for root, dirs, files in os.walk(local):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = Path(root).relative_to(local).as_posix()
        remote_root = remote if not rel or rel == "." else f"{remote}/{rel}"
        mkdir_p(remote_root)
        for d in dirs:
            mkdir_p(f"{remote_root}/{d}")
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                continue
            lp = Path(root) / f
            rp = f"{remote_root}/{f}"
            print(f"  {lp.relative_to(local)}")
            sftp.put(str(lp), rp)


def local_prod_backup(yes: bool) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = LOCAL_BACKUPS / f"prod_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print(f"1/4 本地备份 -> {backup_dir}")
    print("=" * 60)

    if not PYTHON.is_file():
        raise SystemExit(f"找不到 Python: {PYTHON}")

    cmd = [str(PYTHON), str(SYNC_SCRIPT), "--yes", "--skip-restore"]
    if yes:
        pass
    print("拉取生产 SQL + uploads ...")
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    sync_dir = BACKEND_LOCAL / ".sync"
    sql_files = sorted(sync_dir.glob("prod_qipai_*.sql"), reverse=True)
    if sql_files:
        shutil.copy2(sql_files[0], backup_dir / sql_files[0].name)
        print(f"  SQL: {sql_files[0].name}")
    uploads_src = BACKEND_LOCAL / "uploads"
    if uploads_src.is_dir():
        shutil.copytree(uploads_src, backup_dir / "uploads", dirs_exist_ok=True)
        count = sum(1 for _ in (backup_dir / "uploads").rglob("*") if _.is_file())
        print(f"  附件: {count} 个文件")

    readme = backup_dir / "README.txt"
    readme.write_text(
        f"生产环境备份 {ts}\n来源: {HOST}\n包含: PostgreSQL plain SQL + uploads/\n",
        encoding="utf-8",
    )
    print(f"本地备份完成: {backup_dir}")
    return backup_dir


def build_frontend() -> None:
    print("\n构建前端 (base=/qipai/) ...")
    subprocess.run(["npm", "install"], cwd=str(FRONTEND_LOCAL), check=True, shell=True)
    subprocess.run(
        ["npm", "run", "build", "--", "--base=/qipai/"],
        cwd=str(FRONTEND_LOCAL),
        check=True,
        shell=True,
    )
    if not LOCAL_DIST.is_dir():
        raise SystemExit(f"构建失败，缺少 {LOCAL_DIST}")


def ensure_env_upload_vars(ssh: paramiko.SSHClient) -> None:
    env_path = f"{BACKEND_REMOTE}/.env"
    run(ssh, f"grep -q '^UPLOAD_DIR=' {env_path} || echo 'UPLOAD_DIR={UPLOADS_REMOTE}' >> {env_path}")
    run(ssh, f"grep -q '^UPLOAD_URL_PREFIX=' {env_path} || echo 'UPLOAD_URL_PREFIX=/uploads' >> {env_path}")
    run(ssh, f"sed -i 's|^UPLOAD_URL_PREFIX=/qipai/uploads|UPLOAD_URL_PREFIX=/uploads|' {env_path}")


def remote_backup_and_deploy(skip_local_backup: bool, yes: bool) -> None:
    if not skip_local_backup:
        local_prod_backup(yes)

    build_frontend()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"\n连接 {USER}@{HOST} ...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    _, ts_out, _ = run(ssh, "date +%Y%m%d_%H%M%S")
    ts = ts_out.strip()
    backup = f"/www/backup/qipai_{ts}"

    print("=" * 60)
    print(f"2/4 线上备份 -> {backup}")
    print("=" * 60)
    run(ssh, f"mkdir -p {backup}/{{db,site,code,uploads}}")

    run(
        ssh,
        f"""bash -lc '
set -e
cd {BACKEND_REMOTE}
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
pg_dump -h 127.0.0.1 -U qipai -d qipai -F c -f {backup}/db/qipai_{ts}.dump
ls -lh {backup}/db/qipai_{ts}.dump
'""",
        timeout=300,
    )
    run(
        ssh,
        f"tar -czf {backup}/site/qipai_frontend_{ts}.tar.gz -C /www/wwwroot/jb.jxfgg.com qipai 2>/dev/null || true",
        timeout=180,
    )
    run(
        ssh,
        f"tar -czf {backup}/code/qipai_code_{ts}.tar.gz --exclude=.venv --exclude=__pycache__ -C /www/server qipai",
        timeout=300,
    )
    run(
        ssh,
        f"[ -d {UPLOADS_REMOTE} ] && tar -czf {backup}/uploads/uploads_{ts}.tar.gz -C {BACKEND_REMOTE} uploads || echo no uploads",
        timeout=180,
    )

    print("=" * 60)
    print("3/4 上传后端 + 执行迁移")
    print("=" * 60)
    sftp = ssh.open_sftp()
    try:
        for sub in ("app", "scripts"):
            print(f"\n上传 backend/{sub}/ ...")
            sftp_upload_dir(sftp, BACKEND_LOCAL / sub, f"{BACKEND_REMOTE}/{sub}")
        run(ssh, f"mkdir -p {SQL_REMOTE}")
        for sql_name in (
            "06-expense-attachment-file.sql",
            "07-expense-voided.sql",
        ):
            local_sql = ROOT / "sql" / "supabase" / sql_name
            if local_sql.is_file():
                sftp.put(str(local_sql), f"{SQL_REMOTE}/{sql_name}")
        print(f"\n上传前端 dist/ -> {FRONTEND_REMOTE}")
        sftp_upload_dir(sftp, LOCAL_DIST, FRONTEND_REMOTE)
    finally:
        sftp.close()

    ensure_env_upload_vars(ssh)
    run(ssh, f"mkdir -p {UPLOADS_REMOTE}")

    migrate = f"""
cd {BACKEND_REMOTE}
source .venv/bin/activate
pip install -r requirements.txt -q
python -m scripts.apply_expense_attachment_file
python -m scripts.apply_expense_void
python -m scripts.check_db
deactivate
"""
    code, _, _ = run(ssh, f"bash -lc '{migrate}'", timeout=600)
    if code != 0:
        ssh.close()
        raise SystemExit("后端迁移失败")

    print("=" * 60)
    print("4/4 重启服务并验证")
    print("=" * 60)
    for cmd in (
        "supervisorctl restart qipai-api",
        "/www/server/panel/pyenv/bin/supervisorctl restart qipai-api",
    ):
        c, o, _ = run(ssh, cmd)
        if c == 0:
            break

    run(ssh, "curl -s http://127.0.0.1:8000/health")
    run(ssh, "curl -s -o /dev/null -w 'frontend:%{http_code}\\n' http://127.0.0.1/qipai/ 2>/dev/null || true")
    print("\n部署完成: https://jb.jxfgg.com/qipai/")
    ssh.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="生产备份与部署")
    parser.add_argument("--yes", action="store_true", help="跳过确认")
    parser.add_argument("--backup-only", action="store_true", help="仅本地+线上备份，不部署")
    parser.add_argument("--skip-local-backup", action="store_true", help="跳过从生产拉取到本地")
    args = parser.parse_args()

    if not args.yes:
        ans = input("将备份并部署到生产环境，确认？(yes/no): ").strip().lower()
        if ans not in ("yes", "y"):
            print("已取消")
            return 0

    if args.backup_only:
        local_prod_backup(True)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
        _, ts_out, _ = run(ssh, "date +%Y%m%d_%H%M%S")
        ts = ts_out.strip()
        backup = f"/www/backup/qipai_{ts}"
        run(ssh, f"mkdir -p {backup}/db")
        run(
            ssh,
            f"""bash -lc 'cd {BACKEND_REMOTE} && PASS=$(python3 -c "import re;from pathlib import Path;t=Path(\\".env\\").read_text();m=re.search(r\\"://([^:]+):([^@]+)@\\", re.search(r\\"DATABASE_URL=(.+)\\", t).group(1));print(m.group(2))") && PGPASSWORD=$PASS pg_dump -h 127.0.0.1 -U qipai -d qipai -F c -f {backup}/db/qipai_{ts}.dump && ls -lh {backup}/db/'""",
            timeout=300,
        )
        ssh.close()
        print("\n备份完成（未部署）")
        return 0

    remote_backup_and_deploy(args.skip_local_backup, args.yes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
