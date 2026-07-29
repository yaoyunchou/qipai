# 棋牌室云端网页开单系统

云端网页版棋牌室记账开单系统。

技术栈：**React (Vite)** + **Python FastAPI** + **PostgreSQL**（本地 / Supabase / 宝塔自建库均可）

## 快速启动

> 详细说明、部署与排错见 [code/README.md](code/README.md)

### 1. 首次：配置数据库

```powershell
cd code
copy backend\.env.example backend\.env
# 编辑 backend\.env，填入 DATABASE_URL、JWT_SECRET
.\setup-db.ps1
```

`setup-db.ps1` 会建表并创建默认管理员（`admin` / `admin123`）。

若库中已有报销模块且附件仍是 Base64 存储，需额外执行：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m scripts.apply_expense_attachment_file
python -m scripts.migrate_expense_attachments
```

### 2. 启动前后端

在 `code/` 目录下：

```powershell
.\start.ps1
```

或双击 `start.cmd`。

| 服务 | 地址 |
|------|------|
| 前端 | http://127.0.0.1:5180 |
| API 文档 | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/health |

按 `Ctrl+C` 可同时停止前后端。

### 同步生产数据到 Supabase（与线上一致）

本地 `.env` 指向 Supabase 时，一键把**生产库 + 附件**同步过来（会覆盖 Supabase 里 public 数据）：

```powershell
cd code\backend
.\.venv\Scripts\python.exe -m pip install paramiko python-dotenv
cd ..\..
code\backend\.venv\Scripts\python.exe scripts\sync_prod_to_dev.py --yes
```

或：

```powershell
cd code
.\sync-prod-to-dev.ps1 --yes
```

同步后确认 `.env`：

```env
UPLOAD_DIR=uploads
UPLOAD_URL_PREFIX=/uploads
```

### 3. 手动启动（可选）

```powershell
# 后端
cd code\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（另开终端）
cd code\frontend
npm install
npm run dev
```

## 文档

| 文件 | 说明 |
|------|------|
| [需求文档.md](需求文档.md) | **主文档**：角色权限、开单、后台、报表、范围外功能 |
| [code/README.md](code/README.md) | **代码**：完整启动、部署（Vercel / 宝塔）、环境变量 |
| [sql/README.md](sql/README.md) | **数据库**：MySQL 历史脚本 + [Supabase](sql/supabase/README.md) 初始化 |
| [_source.txt](_source.txt) | 源 Word 文档段落提取（对照用） |

## 源文件

- 原始开发文档：`棋牌室云端网页开单系统 · 最终开发文档 (1).docx`（微信文件目录）

## 核心结论（一句话）

纯记账、无计时无收款；四角色（收银员 / 经理 / 股东 / 超管）；前台绿红桌台开单清台；超管管台位与基准价；报表日周月，股东只看汇总无明细。