"""一次性远程部署：备份 → 拉代码 → 迁移 → 重启后端 → 上传前端。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import paramiko

HOST = "1.12.219.199"
USER = "root"
PASSWORD = os.environ.get("QIPAI_SSH_PASSWORD", "Jxfg357159..")
CODE_DIR = "/www/server/qipai"
BACKEND_DIR = f"{CODE_DIR}/code/backend"
FRONTEND_REMOTE = "/www/wwwroot/jb.jxfgg.com/qipai"
UPLOADS_DIR = f"{BACKEND_DIR}/uploads"
LOCAL_DIST = Path(__file__).resolve().parents[1] / "code" / "frontend" / "dist"


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
    print(f"\n>>> {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    return code, out, err


def sftp_upload_dir(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    def _mkdir_p(path: str) -> None:
        parts = path.strip("/").split("/")
        cur = ""
        for p in parts:
            cur += f"/{p}"
            try:
                sftp.mkdir(cur)
            except OSError:
                pass

    _mkdir_p(remote)

    for root, dirs, files in os.walk(local):
        rel = Path(root).relative_to(local).as_posix()
        remote_root = remote if not rel or rel == "." else f"{remote}/{rel}"
        _mkdir_p(remote_root)
        for d in dirs:
            _mkdir_p(f"{remote_root}/{d}")
        for f in files:
            lp = Path(root) / f
            rp = f"{remote_root}/{f}"
            print(f"  upload {lp.name} -> {rp}")
            sftp.put(str(lp), rp)


def ensure_env_upload_vars(ssh: paramiko.SSHClient) -> None:
    env_path = f"{BACKEND_DIR}/.env"
    _, out, _ = run(ssh, f"grep -E '^UPLOAD_' {env_path} || true")
    if "UPLOAD_DIR" in out and "UPLOAD_URL_PREFIX" in out:
        print("UPLOAD_* 已存在于 .env，跳过")
        return
    append = (
        f"\nUPLOAD_DIR={UPLOADS_DIR}\n"
        f"UPLOAD_URL_PREFIX=/uploads\n"
    )
    run(ssh, f"grep -q '^UPLOAD_DIR=' {env_path} || echo 'UPLOAD_DIR={UPLOADS_DIR}' >> {env_path}")
    run(ssh, f"grep -q '^UPLOAD_URL_PREFIX=' {env_path} || echo 'UPLOAD_URL_PREFIX=/uploads' >> {env_path}")
    # 修正旧配置 /qipai/uploads → /uploads（避免前端 BASE_URL 重复拼接）
    run(ssh, f"sed -i 's|^UPLOAD_URL_PREFIX=/qipai/uploads|UPLOAD_URL_PREFIX=/uploads|' {env_path}")


def ensure_nginx_uploads(ssh: paramiko.SSHClient) -> None:
    snippet = """
    location /qipai/uploads/ {
        alias /www/server/qipai/code/backend/uploads/;
        expires 30d;
        access_log off;
    }
"""
    check_cmd = (
        "grep -r 'location /qipai/uploads/' /www/server/panel/vhost/nginx/ 2>/dev/null | head -1"
    )
    code, out, _ = run(ssh, check_cmd)
    if out.strip():
        print("Nginx uploads location 已存在，跳过")
        return
    # 尝试 jb.jxfgg.com 配置
    conf_candidates = [
        "/www/server/panel/vhost/nginx/jb.jxfgg.com.conf",
        "/www/server/panel/vhost/nginx/extension/jb.jxfgg.com/*.conf",
    ]
    for pattern in conf_candidates:
        run(ssh, f'for f in {pattern}; do [ -f "$f" ] && echo "$f"; done')
    # 在 jb.jxfgg.com.conf 的 server 块末尾前插入（在最后一个 } 前）
    conf = "/www/server/panel/vhost/nginx/jb.jxfgg.com.conf"
    marker = "location /qipai/uploads/"
    insert_cmd = (
        "python3 - <<'PY'\n"
        "from pathlib import Path\n"
        f'conf = Path("{conf}")\n'
        "if not conf.exists():\n"
        '    print("conf not found:", conf)\n'
        "    raise SystemExit(0)\n"
        "text = conf.read_text(encoding=\"utf-8\")\n"
        f'if "{marker}" in text:\n'
        '    print("already patched")\n'
        "    raise SystemExit(0)\n"
        "block = '''    location /qipai/uploads/ {\\n"
        "        alias /www/server/qipai/code/backend/uploads/;\\n"
        "        expires 30d;\\n"
        "        access_log off;\\n"
        "    }\\n\\n'''\n"
        "idx = text.rfind('\\n}')\n"
        "if idx == -1:\n"
        '    print("no closing brace")\n'
        "    raise SystemExit(1)\n"
        "new_text = text[:idx] + '\\n' + block + text[idx:]\n"
        "conf.write_text(new_text, encoding=\"utf-8\")\n"
        'print("nginx conf patched")\n'
        "PY"
    )
    run(ssh, insert_cmd)
    run(ssh, "nginx -t && nginx -s reload")


def main() -> int:
    if not LOCAL_DIST.is_dir():
        print(f"缺少前端构建产物: {LOCAL_DIST}", file=sys.stderr)
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"连接 {USER}@{HOST} ...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    ts_cmd = 'date +%Y%m%d_%H%M%S'
    _, ts_out, _ = run(ssh, ts_cmd)
    ts = ts_out.strip()
    backup = f"/www/backup/qipai_{ts}"
    run(ssh, f"mkdir -p {backup}/{{db,site,code,uploads}}")

    # 备份：数据库（从 .env 解析密码）
    run(
        ssh,
        f"""bash -lc '
set -e
cd {BACKEND_DIR}
source .venv/bin/activate 2>/dev/null || true
URL=$(grep ^DATABASE_URL= .env | cut -d= -f2-)
# postgresql+psycopg2://qipai:PASS@127.0.0.1:5432/qipai
PASS=$(python3 - <<PY
import os, re
from pathlib import Path
url = Path(".env").read_text(encoding="utf-8")
m = re.search(r"DATABASE_URL=(.+)", url)
if not m: raise SystemExit(1)
line = m.group(1).strip()
m2 = re.search(r"://([^:]+):([^@]+)@", line)
print(m2.group(2) if m2 else "")
PY
)
PGPASSWORD="$PASS" pg_dump -h 127.0.0.1 -U qipai -d qipai -F c -f {backup}/db/qipai_{ts}.dump
echo DB backup ok
'""",
        timeout=300,
    )

    run(
        ssh,
        f"tar -czf {backup}/site/qipai_frontend_{ts}.tar.gz -C /www/wwwroot/jb.jxfgg.com qipai 2>/dev/null || true",
        timeout=120,
    )
    run(
        ssh,
        f"tar -czf {backup}/code/qipai_code_{ts}.tar.gz --exclude=.venv --exclude=__pycache__ -C /www/server qipai",
        timeout=300,
    )
    run(
        ssh,
        f"[ -d {UPLOADS_DIR} ] && tar -czf {backup}/uploads/uploads_{ts}.tar.gz -C {BACKEND_DIR} uploads || echo no uploads yet",
    )
    run(ssh, f"ls -lh {backup}/db/ {backup}/site/ {backup}/code/ 2>/dev/null || true")

    # 拉代码
    run(ssh, f"cd {CODE_DIR} && git pull origin main", timeout=120)

    ensure_env_upload_vars(ssh)
    run(ssh, f"mkdir -p {UPLOADS_DIR}")

    # 后端依赖 + 迁移
    backend_cmds = f"""
cd {BACKEND_DIR}
source .venv/bin/activate
pip install -r requirements.txt -q
python -m scripts.apply_expense_attachment_file
python -m scripts.migrate_expense_attachments
python -m scripts.check_db
deactivate
"""
    code, _, err = run(ssh, f"bash -lc '{backend_cmds}'", timeout=600)
    if code != 0:
        print("后端迁移失败", file=sys.stderr)
        ssh.close()
        return code

    # 重启 supervisor
    for cmd in (
        "supervisorctl restart qipai-api",
        "/www/server/panel/pyenv/bin/supervisorctl restart qipai-api",
        "systemctl restart supervisord && supervisorctl restart qipai-api",
    ):
        c, o, _ = run(ssh, cmd)
        if c == 0 and ("started" in o.lower() or "restart" in o.lower() or o.strip() == ""):
            break

    run(ssh, "curl -s http://127.0.0.1:8000/health")

    ensure_nginx_uploads(ssh)

    # 上传前端
    print(f"\n上传前端 {LOCAL_DIST} -> {FRONTEND_REMOTE}")
    sftp = ssh.open_sftp()
    try:
        sftp_upload_dir(sftp, LOCAL_DIST, FRONTEND_REMOTE)
    finally:
        sftp.close()

    run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health")
    print("\n部署完成。请浏览器验证: https://jb.jxfgg.com/qipai/")
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
