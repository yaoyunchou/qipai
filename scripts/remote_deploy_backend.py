"""SFTP 上传 backend 代码（排除 .venv）并执行迁移。"""
from __future__ import annotations

import os
from pathlib import Path

import paramiko

HOST = "1.12.219.199"
USER = "root"
PASSWORD = os.environ.get("QIPAI_SSH_PASSWORD", "Jxfg357159..")
BACKEND_LOCAL = Path(__file__).resolve().parents[1] / "code" / "backend"
BACKEND_REMOTE = "/www/server/qipai/code/backend"
SQL_REMOTE = "/www/server/qipai/sql/supabase"


def run(ssh, cmd, timeout=600):
    print(f"\n>>> {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip())
    return code, out, err


def upload_tree(sftp, local: Path, remote: str, skip_dirs: set[str]) -> None:
    for root, dirs, files in os.walk(local):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = Path(root).relative_to(local).as_posix()
        remote_dir = remote if rel == "." else f"{remote}/{rel}"
        try:
            sftp.mkdir(remote_dir)
        except OSError:
            pass
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                continue
            lp = Path(root) / f
            rp = f"{remote_dir}/{f}"
            print(f"  {lp.relative_to(local)}")
            sftp.put(str(lp), rp)


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    sftp = ssh.open_sftp()

    print("上传 app/ scripts/ ...")
    for sub in ("app", "scripts"):
        upload_tree(sftp, BACKEND_LOCAL / sub, f"{BACKEND_REMOTE}/{sub}", set())

    sql_local = Path(__file__).resolve().parents[1] / "sql" / "supabase" / "06-expense-attachment-file.sql"
    run(ssh, f"mkdir -p {SQL_REMOTE}")
    sftp.put(str(sql_local), f"{SQL_REMOTE}/06-expense-attachment-file.sql")
    sftp.close()

    migrate = f"""
cd {BACKEND_REMOTE}
source .venv/bin/activate
pip install -r requirements.txt -q
python -m scripts.apply_expense_attachment_file
python -m scripts.migrate_expense_attachments
python -m scripts.check_db
deactivate
supervisorctl restart qipai-api
curl -s http://127.0.0.1:8000/health
"""
    run(ssh, f"bash -lc '{migrate}'", timeout=600)
    ssh.close()
    print("后端代码上传并迁移完成")


if __name__ == "__main__":
    main()
