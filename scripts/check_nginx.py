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


def run(cmd: str) -> None:
    _, o, e = ssh.exec_command(cmd)
    print(">>>", cmd)
    print(o.read().decode("utf-8", errors="replace") or e.read().decode("utf-8", errors="replace"))


run("ls /www/server/qipai/code/backend/uploads/expenses/1/")
run("grep -n upload /www/server/qipai/code/backend/app/main.py")
run("grep UPLOAD /www/server/qipai/code/backend/.env")
run("sed -n '48,110p' /www/server/panel/vhost/nginx/jb.jxfgg.com.conf")
run(
    "curl -s -o /dev/null -w '%{http_code}' "
    "http://127.0.0.1:8000/uploads/expenses/32/9167c1fe2fc3458e8a3f6187d85b0b2c.jpeg"
)
ssh.close()
