# 变更日志

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

## 2026-06-16

- 新增 Vercel 部署配置：`vercel.json`、`pyproject.toml`、`api/index.py`、`scripts/vercel_build.py`
- 后端适配 Serverless：`database.py` 在 Vercel 环境使用 `NullPool`；`config.py` 自动追加 `VERCEL_URL` 到 CORS
- `README.md` 补充「部署到 Vercel + Supabase」章节
- `.gitignore` 增加 `.vercel/`

## 2026-06-09

- 新增 `start.ps1` / `start.cmd`：一键启动前后端，自动检测并安装缺失依赖，首次运行初始化 admin
- 前端开发端口由 5173 改为 **5180**（`vite.config.ts`、后端 CORS 同步）
- 更新 `README.md` 一键启动说明
