# 变更日志

## 2026-06-16

- 新增 Vercel 部署配置：`vercel.json`、`pyproject.toml`、`api/index.py`、`scripts/vercel_build.py`
- 后端适配 Serverless：`database.py` 在 Vercel 环境使用 `NullPool`；`config.py` 自动追加 `VERCEL_URL` 到 CORS
- `README.md` 补充「部署到 Vercel + Supabase」章节
- `.gitignore` 增加 `.vercel/`

## 2026-06-09

- 新增 `start.ps1` / `start.cmd`：一键启动前后端，自动检测并安装缺失依赖，首次运行初始化 admin
- 前端开发端口由 5173 改为 **5180**（`vite.config.ts`、后端 CORS 同步）
- 更新 `README.md` 一键启动说明
