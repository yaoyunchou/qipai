import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    "1.12.219.199",
    username="root",
    password=os.environ.get("QIPAI_SSH_PASSWORD", "Jxfg357159.."),
    timeout=30,
)

env = "/www/server/qipai/code/backend/.env"
cmds = [
    f"sed -i 's|^UPLOAD_URL_PREFIX=/qipai/uploads|UPLOAD_URL_PREFIX=/uploads|' {env}",
    f"grep UPLOAD {env}",
    "supervisorctl restart qipai-api",
    "sleep 1",
    "curl -s http://127.0.0.1:8000/health",
]
for c in cmds:
    _, o, e = ssh.exec_command(c)
    print(">>>", c)
    print(o.read().decode() or e.read().decode())

# upload frontend dist
from pathlib import Path

local = Path(__file__).resolve().parents[1] / "code" / "frontend" / "dist"
remote = "/www/wwwroot/jb.jxfgg.com/qipai"
sftp = ssh.open_sftp()


def upload_dir(local_dir: Path, remote_dir: str) -> None:
    import os

    for root, _, files in os.walk(local_dir):
        rel = Path(root).relative_to(local_dir).as_posix()
        rdir = remote_dir if rel == "." else f"{remote_dir}/{rel}"
        try:
            sftp.mkdir(rdir)
        except OSError:
            pass
        for f in files:
            sftp.put(str(Path(root) / f), f"{rdir}/{f}")
            print("upload", f)


upload_dir(local, remote)
sftp.close()
ssh.close()
print("done")
