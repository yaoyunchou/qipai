# 变更日志

## 2026-07-23

- 报销附件由数据库 Base64 改为**磁盘静态文件**：上传落盘至 `backend/uploads/expenses/{claim_id}/{uuid}.ext`，DB 仅存 `file_path`；列表/详情 API 返回 `url` 不再带图片内容，解决列表接口 24MB/24 秒问题
- 本地开发：FastAPI 挂载 `/uploads` 静态目录，Vite 代理 `/uploads` → 8000
- 迁移：`sql/supabase/06-expense-attachment-file.sql` + `scripts.apply_expense_attachment_file` + `scripts.migrate_expense_attachments`（旧库 Base64 导出为文件）
- 生产 Nginx 需增加 `location /qipai/uploads/` alias 到 uploads 目录，并配置 `UPLOAD_DIR`、`UPLOAD_URL_PREFIX=/qipai/uploads`

## 2026-07-03

- 股东（SHAREHOLDER）权限调整：开放开台看板访问权限（`tables.py` 移除 403 限制）、可查看自己名下的订单（`orders.py`）、前端取消强制跳转 `/reports`（`Floor.tsx`）
- 新增宝塔面板生产环境部署文档 `DEPLOY.md` 与一键部署脚本 `deploy.sh`
- `backend/requirements.txt` 锁定 `greenlet==3.1.1`：`greenlet` 3.5.x 未提供 cp310 manylinux 预编译包，在旧 glibc（CentOS 7）环境安装时会触发源码编译失败
- **完成首次生产部署**（腾讯云 1.12.219.199 + 宝塔面板，CentOS 7）：
  - 通过 PGDG 归档仓库安装 PostgreSQL 15（`/usr/pgsql-15`，仅监听 127.0.0.1，与宝塔自带 MySQL 共存）；新建 `qipai` 库与用户
  - 因 CentOS 7 glibc 2.17 过旧，改用清华 TUNA 镜像的 Miniconda（`Miniconda3-py310_22.11.1`）提供独立 Python 3.10.8，不依赖/不污染系统 Python
  - 后端虚拟环境 + 依赖安装（改用清华 PyPI 镜像，规避阿里云镜像缺失新版 wheel 的问题）、执行 schema 初始化脚本、创建 admin 账号
  - Supervisor（pip 安装 + systemd 托管）守护 `qipai-api`（uvicorn，127.0.0.1:8000）
  - 前端因 Node.js 官方/社区构建包在国内下载极慢，改为**本地构建、SFTP 直传 `dist/`** 到 `/www/wwwroot/jxfgg.com/dist`，跳过服务器装 Node
  - 按宝塔 vhost 规范新增 `jxfgg.com` 站点 Nginx 配置（静态资源 + `/api`、`/health` 反代），验证登录/健康检查接口均正常
  - **待办**：`jxfgg.com` 域名尚未配置 DNS A 记录（需在腾讯云 DNSPod 手动添加指向 `1.12.219.199`），解析生效后再申请 SSL 证书并开启强制 HTTPS；部署验证完成后需收紧服务器 SSH（关闭密码登录、改回仅密钥认证）
- **临时挂载到已有 HTTPS 域名子路径，供 DNS 解析生效前验证**：`jxfgg.com` DNS 未生效期间，借用同服务器已有证书的 `jb.jxfgg.com`，将 qipai 前端临时挂载到 `https://jb.jxfgg.com/qipai/`：
  - 前端支持可配置的部署根路径：`App.tsx` 的 `BrowserRouter` 增加 `basename={import.meta.env.BASE_URL}`，`api/client.ts` 的 `api()`/`downloadFile()` 请求统一加上 `API_BASE` 前缀（取自 `import.meta.env.BASE_URL`），根路径部署（`base` 默认 `/`）行为不受影响
  - 用 `vite build --base=/qipai/` 单独构建一份产物，SFTP 上传到 `jb.jxfgg.com` 站点目录下的 `/www/wwwroot/jb.jxfgg.com/qipai/`
  - 在 `jb.jxfgg.com.conf` 中新增 `/qipai/`、`/qipai/api/`、`/qipai/health` 三个 location（反代到 127.0.0.1:8000，SPA `try_files` 回退到 `/qipai/index.html`），未改动原站点任何配置，验证登录接口、静态资源、原站点均正常
  - 该子路径为临时验证方案，`jxfgg.com` DNS/SSL 就绪后应移除

## 2026-06-16

- 新增 Vercel 部署配置：`vercel.json`、`pyproject.toml`、`api/index.py`、`scripts/vercel_build.py`
- 后端适配 Serverless：`database.py` 在 Vercel 环境使用 `NullPool`；`config.py` 自动追加 `VERCEL_URL` 到 CORS
- `README.md` 补充「部署到 Vercel + Supabase」章节
- `.gitignore` 增加 `.vercel/`

## 2026-06-09

- 新增 `start.ps1` / `start.cmd`：一键启动前后端，自动检测并安装缺失依赖，首次运行初始化 admin
- 前端开发端口由 5173 改为 **5180**（`vite.config.ts`、后端 CORS 同步）
- 更新 `README.md` 一键启动说明
