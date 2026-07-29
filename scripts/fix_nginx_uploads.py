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

fix = r"""python3 - <<'PY'
from pathlib import Path
conf = Path("/www/server/panel/vhost/nginx/jb.jxfgg.com.conf")
text = conf.read_text(encoding="utf-8")
old = "location /qipai/uploads/ {"
new = "location ^~ /qipai/uploads/ {"
if old in text:
    text = text.replace(old, new, 1)
    conf.write_text(text, encoding="utf-8")
    print("patched ^~")
elif new in text:
    print("already ^~")
else:
    print("uploads block not found")
PY
nginx -t && nginx -s reload
curl -s -o /dev/null -w "nginx_upload:%{http_code}\n" -H "Host: jb.jxfgg.com" "http://127.0.0.1/qipai/uploads/expenses/1/71283e7cdd68448d94eaa0065f65cfd5.png"
"""

_, o, e = ssh.exec_command(fix)
print(o.read().decode())
print(e.read().decode())
ssh.close()
