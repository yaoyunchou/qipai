# 变更日志

## 2026-07-03

- 股东（SHAREHOLDER）权限调整：开放开台看板访问权限（`tables.py` 移除 403 限制）、可查看自己名下的订单（`orders.py`）、前端取消强制跳转 `/reports`（`Floor.tsx`）
- 新增宝塔面板生产环境部署文档 `DEPLOY.md` 与一键部署脚本 `deploy.sh`

## 2026-06-16

- 新增 Vercel 部署配置：`vercel.json`、`pyproject.toml`、`api/index.py`、`scripts/vercel_build.py`
- 后端适配 Serverless：`database.py` 在 Vercel 环境使用 `NullPool`；`config.py` 自动追加 `VERCEL_URL` 到 CORS
- `README.md` 补充「部署到 Vercel + Supabase」章节
- `.gitignore` 增加 `.vercel/`

## 2026-06-09

- 新增 `start.ps1` / `start.cmd`：一键启动前后端，自动检测并安装缺失依赖，首次运行初始化 admin
- 前端开发端口由 5173 改为 **5180**（`vite.config.ts`、后端 CORS 同步）
- 更新 `README.md` 一键启动说明
