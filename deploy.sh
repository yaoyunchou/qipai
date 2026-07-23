#!/bin/bash
set -e

# ========== 0. 变量配置（部署前必须检查/修改）==========
REPO_SSH="git@github.com:yaoyunchou/qipai.git"
REPO_HTTPS="https://github.com/yaoyunchou/qipai.git"
CODE_DIR="/www/server/qipai"
SITE_DIR="/www/wwwroot/jxfgg.com"
DB_NAME="qipai"
DB_USER="qipai"
DB_PASS="改成你在宝塔PostgreSQL里创建qipai用户时设置的密码"   # <<< 必填
CORS_ORIGINS="https://jxfgg.com,https://www.jxfgg.com"
BACKUP_DIR="/www/backup"
TS=$(date +%Y%m%d_%H%M%S)

echo "===================================================="
echo " 1/7 环境检查"
echo "===================================================="
for cmd in git python3 node npm psql nginx; do
  if command -v $cmd >/dev/null 2>&1; then
    echo "  [OK] $cmd"
  else
    echo "  [缺失] $cmd —— 请先在宝塔软件商店安装对应软件！"
  fi
done

echo "===================================================="
echo " 2/7 备份（等价于宝塔的『网站』+『数据库』备份）"
echo "===================================================="
mkdir -p "$BACKUP_DIR/site" "$BACKUP_DIR/database"

if [ -d "$SITE_DIR" ]; then
  tar -czf "$BACKUP_DIR/site/jxfgg.com_${TS}.tar.gz" -C "$(dirname "$SITE_DIR")" "$(basename "$SITE_DIR")"
  echo "  站点目录已备份 -> $BACKUP_DIR/site/jxfgg.com_${TS}.tar.gz"
else
  echo "  站点目录不存在（首次部署），跳过"
fi

if [ -d "$CODE_DIR" ]; then
  tar -czf "$BACKUP_DIR/site/qipai_code_${TS}.tar.gz" -C "$(dirname "$CODE_DIR")" "$(basename "$CODE_DIR")"
  echo "  旧源码已备份 -> $BACKUP_DIR/site/qipai_code_${TS}.tar.gz"
fi

if PGPASSWORD="$DB_PASS" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -c '\q' >/dev/null 2>&1; then
  PGPASSWORD="$DB_PASS" pg_dump -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_DIR/database/${DB_NAME}_${TS}.dump"
  echo "  数据库已备份 -> $BACKUP_DIR/database/${DB_NAME}_${TS}.dump"
else
  echo "  数据库不存在或连接失败（首次部署，或密码未填对），跳过数据库备份"
fi

echo "===================================================="
echo " 3/7 拉取 / 更新代码"
echo "===================================================="
mkdir -p /www/server
if [ -d "$CODE_DIR/.git" ]; then
  cd "$CODE_DIR"
  git pull origin main
else
  git clone "$REPO_SSH" "$CODE_DIR" 2>/dev/null || git clone "$REPO_HTTPS" "$CODE_DIR"
fi
cd "$CODE_DIR/code"

echo "===================================================="
echo " 4/7 配置 backend/.env"
echo "===================================================="
if [ ! -f backend/.env ]; then
  JWT_SECRET=$(openssl rand -hex 32)
  cat > backend/.env <<EOF
DATABASE_URL=postgresql+psycopg2://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
DATABASE_SSL_MODE=
JWT_SECRET=${JWT_SECRET}
CORS_ORIGINS=${CORS_ORIGINS}
EOF
  chmod 600 backend/.env
  echo "  已生成 backend/.env，JWT_SECRET=${JWT_SECRET}（请记录，勿泄露）"
else
  echo "  backend/.env 已存在，跳过（如需改配置请手动编辑该文件）"
fi

echo "===================================================="
echo " 5/7 安装后端依赖 & 初始化数据库"
echo "===================================================="
cd "$CODE_DIR/code/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

TABLE_COUNT=$(PGPASSWORD="$DB_PASS" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -tAc \
  "select count(*) from information_schema.tables where table_schema='public'" 2>/dev/null || echo 0)

if [ "$TABLE_COUNT" -eq 0 ]; then
  echo "  首次部署，执行数据库初始化脚本..."
  python -m scripts.apply_schema
  python -m scripts.apply_expense_schema
  python -m scripts.apply_expense_category
  echo "  >>> 请手动执行以下命令创建管理员账号（设置强密码）："
  echo "      cd $CODE_DIR/code/backend && source .venv/bin/activate && python -m scripts.init_admin <你的管理员密码>"
else
  echo "  已检测到 $TABLE_COUNT 张表，跳过初始化（如需补丁请手动执行对应 scripts）"
fi

python -m scripts.check_db || echo "  数据库连通性检查失败，请检查 .env 中的 DATABASE_URL"
deactivate

echo "===================================================="
echo " 6/7 构建前端"
echo "===================================================="
cd "$CODE_DIR/code/frontend"
npm install
npm run build
mkdir -p "$SITE_DIR"
rm -rf "$SITE_DIR/dist"
cp -r dist "$SITE_DIR/"
echo "  前端已构建并部署到 $SITE_DIR/dist"

echo "===================================================="
echo " 7/7 完成！接下来请手动做的事"
echo "===================================================="
cat <<'EOF'

  1) 宝塔 -> Supervisor 管理器 -> 添加守护进程：
       名称:      qipai-api
       运行目录:  /www/server/qipai/code/backend
       启动命令:  /www/server/qipai/code/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
       用户:      www 或 root

  2) 宝塔 -> 网站 -> jxfgg.com -> 配置文件，在 server{} 内加入：
       root /www/wwwroot/jxfgg.com/dist;
       index index.html;
       location / { try_files $uri $uri/ /index.html; }
       location /api {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       location /health { proxy_pass http://127.0.0.1:8000; }
       location /qipai/uploads/ {
           alias /www/server/qipai/code/backend/uploads/;
           expires 30d;
           access_log off;
       }

  3) 宝塔 -> 网站 -> jxfgg.com -> SSL -> Let's Encrypt 申请证书，开启强制HTTPS

  4) 验证：curl http://127.0.0.1:8000/health   应返回 {"status":"ok"}
           curl https://jxfgg.com/health        应返回 {"status":"ok"}

  5) 若首次部署，别忘了执行第5步提示的 init_admin 命令创建管理员账号！

EOF
echo "脚本执行完毕。"