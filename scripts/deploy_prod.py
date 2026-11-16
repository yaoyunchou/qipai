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

# 生产需要补齐的迁移（按顺序、全部幂等，可重复执行）
MIGRATIONS: tuple[str, ...] = (
    "05-expense-category.sql",
    "06-expense-attachment-file.sql",
    "07-expense-voided.sql",
    "08-expense-category-living.sql",
    "09-play-companion.sql",
    "10-play-companion-signed-amount.sql",
    "11-loan-record.sql",
)

# 与上面的 SQL 一一对应的执行脚本（scripts.apply_xxx）
MIGRATION_SCRIPTS: tuple[str, ...] = (
    "apply_expense_category",
    "apply_expense_attachment_file",
    "apply_expense_void",
    "apply_expense_category_living",
    "apply_play_companion",
    "apply_play_companion_signed_amount",
    "apply_loan_record",
)


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
    print("=" * 60)
    print("3/4 上传迁移脚本 + 执行迁移（先迁移，避免新代码引用不存在的表）")
    print("=" * 60)
    sftp = ssh.open_sftp()
    try:
        run(ssh, f"mkdir -p {SQL_REMOTE}")
        # 上传 backend/scripts 下的迁移执行器（app 代码稍后上传，先不动运行中的服务）
        sftp_upload_dir(sftp, BACKEND_LOCAL / "scripts", f"{BACKEND_REMOTE}/scripts")
        for sql_name in MIGRATIONS:
            local_sql = ROOT / "sql" / "supabase" / sql_name
            if local_sql.is_file():
                sftp.put(str(local_sql), f"{SQL_REMOTE}/{sql_name}")
                print(f"  {sql_name}")
            else:
                print(f"  [跳过] 本地缺少 {sql_name}")
    finally:
        sftp.close()

    ensure_env_upload_vars(ssh)
    run(ssh, f"mkdir -p {UPLOADS_REMOTE}")

    migrate_cmds = "\n".join(f"python -m scripts.{m}" for m in MIGRATION_SCRIPTS)
    migrate = f"""
cd {BACKEND_REMOTE}
source .venv/bin/activate
pip install -r requirements.txt -q
{migrate_cmds}
python -m scripts.check_db
deactivate
"""
    code, _, _ = run(ssh, f"bash -lc '{migrate}'", timeout=600)
    if code != 0:
        ssh.close()
        raise SystemExit("后端迁移失败！已停止部署，线上代码未改动。")

    print("=" * 60)
    print("4/4 上传新代码 → 构建产物 → 重启服务")
    print("=" * 60)
    sftp = ssh.open_sftp()
    try:
        print("\n上传 backend/app/ ...")
        sftp_upload_dir(sftp, BACKEND_LOCAL / "app", f"{BACKEND_REMOTE}/app")
        print(f"\n上传前端 dist/ -> {FRONTEND_REMOTE}")
        sftp_upload_dir(sftp, LOCAL_DIST, FRONTEND_REMOTE)
    finally:
        sftp.close()

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


def _git(*args: str) -> tuple[int, str]:
    """执行 git 命令，返回 (退出码, 输出)。"""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "").strip()


def verify_release_ready(release_branch: str, allow_dirty: bool) -> None:
    """部署前置校验：只允许从已合并、无差异的主分支部署。

    规则（任一不满足即中止）：
    1. 当前分支必须是 release_branch（默认 main）
    2. 工作区必须干净（无未提交改动、无未跟踪文件）
    3. 本地分支必须与 origin/<branch> 完全一致（已推送）
    4. 代码必须与 origin/main 一致（无未合并的开发分支差异）
    """
    print("=" * 60)
    print("0/4 部署前置校验")
    print("=" * 60)

    problems: list[str] = []

    code, branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if code != 0:
        raise SystemExit("无法读取当前分支，请确认在项目根目录执行。")
    print(f"  当前分支: {branch}")
    if branch != release_branch:
        problems.append(
            f"当前在 {branch}，必须切换到 {release_branch} 才能部署（禁止任意分支部署）"
        )

    if allow_dirty:
        print("  工作区: 已用 --allow-dirty 跳过检查（不推荐）")
    else:
        code, status = _git("status", "--porcelain")
        if status:
            changed = [ln for ln in status.splitlines() if ln.strip()]
            preview = "\n      ".join(changed[:10])
            more = f"\n      ...还有 {len(changed) - 10} 个" if len(changed) > 10 else ""
            problems.append(f"工作区有 {len(changed)} 个未提交改动，请先提交：\n      {preview}{more}")
        else:
            print("  工作区: 干净")

    code, upstream = _git("rev-parse", "--abbrev-ref", f"{release_branch}@{{upstream}}")
    if code != 0:
        problems.append(f"{release_branch} 未设置上游分支，无法确认是否已推送")
    else:
        code, ahead = _git("rev-list", "--count", f"{upstream}..{release_branch}")
        code2, behind = _git("rev-list", "--count", f"{release_branch}..{upstream}")
        if ahead.isdigit() and int(ahead) > 0:
            problems.append(f"本地 {release_branch} 领先 {upstream} {ahead} 个提交，请先 push")
        if behind.isdigit() and int(behind) > 0:
            problems.append(f"本地 {release_branch} 落后 {upstream} {behind} 个提交，请先 pull")
        if ahead == "0" and behind == "0":
            print(f"  与上游: 一致 ({upstream})")

    # 合并完整性：确认没有游离的开发分支差异（防止漏合并）
    code, diff_origin = _git("rev-list", "--count", f"origin/main..{release_branch}")
    if code == 0 and diff_origin.isdigit() and int(diff_origin) > 0:
        problems.append(f"{release_branch} 与 origin/main 有 {diff_origin} 个提交差异，请先合并并推送")

    # 关键：确认本地代码与远端 main 内容一致（工作区已提交的前提下）
    code, sha = _git("rev-parse", "HEAD")
    code2, main_sha = _git("rev-parse", "origin/main")
    if code == 0 and code2 == 0 and sha != main_sha:
        problems.append(
            "本地 HEAD 与 origin/main 不一致，请先合并到 main 并 push 后再部署\n"
            f"      HEAD        = {sha[:10]}\n"
            f"      origin/main = {main_sha[:10]}"
        )
    elif code == 0 and code2 == 0:
        print(f"  版本一致: {sha[:10]} (origin/main)")

    if problems:
        print("\n部署已中止，存在以下问题：\n")
        for i, p in enumerate(problems, 1):
            print(f"  {i}) {p}")
        print(
            "\n正确流程：\n"
            "  1. 开发分支完成 → 提交\n"
            "  2. 合并到 main（git checkout main && git merge --no-ff <开发分支>）\n"
            "  3. 推送（git push origin main）\n"
            "  4. 确认无差异后，在 main 上执行部署\n"
        )
        raise SystemExit(1)

    print("\n前置校验通过，开始部署。\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="生产备份与部署")
    parser.add_argument("--yes", action="store_true", help="跳过确认")
    parser.add_argument("--backup-only", action="store_true", help="仅本地+线上备份，不部署")
    parser.add_argument("--skip-local-backup", action="store_true", help="跳过从生产拉取到本地")
    parser.add_argument(
        "--release-branch",
        default="main",
        help="允许部署的主分支（默认 main，禁止从其他分支部署）",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="跳过工作区干净检查（仅排障用，不推荐）",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只做部署前置校验，不执行任何部署动作",
    )
    args = parser.parse_args()

    # 前置校验：必须在主分支、已合并、无差异
    verify_release_ready(args.release_branch, args.allow_dirty)

    if args.check:
        print("仅校验模式（--check），未执行任何部署动作。")
        return 0

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
