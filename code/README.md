# 棋牌室云端开单系统 · 代码

技术栈：**React (Vite)** + **Python FastAPI** + **Supabase (PostgreSQL)**

## 一键启动（推荐）

**前置：** 已有 Supabase 项目，并在 `backend/.env` 配置 `DATABASE_URL`。

### 首次：初始化数据库

```powershell
# 1. 复制环境变量模板并填写 Supabase 连接串
copy backend\.env.example backend\.env
# 编辑 backend\.env，填入 DATABASE_URL

# 2. 建表 + 创建 admin 账号
.\setup-db.ps1
```

`setup-db.ps1` 会执行 `sql/supabase/01-init-schema.sql`，并运行 `init_admin`。

**获取连接串：** Supabase Dashboard → Project Settings → Database → Connection string  
推荐使用 **Transaction pooler**（端口 6543），格式示例：

```env
DATABASE_URL=postgresql+psycopg2://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
DATABASE_SSL_MODE=require
JWT_SECRET=dev-secret-change-me
```

### 启动应用

在项目根目录 `code/` 下执行：

```powershell
.\start.ps1
```

或双击 `start.cmd`。

脚本会自动：

| 步骤 | 行为 |
|------|------|
| Python 虚拟环境 | 无 `.venv` 则创建 |
| 后端依赖 | 缺包则 `pip install`，已有则跳过 |
| 数据库连接 | 检测 Supabase `DATABASE_URL` 是否可达 |
| admin 账号 | **仅首次** 执行 `init_admin` |
| 前端依赖 | 无 `node_modules` 则 `npm install`，已有则跳过 |
| 启动服务 | 后端 **8000** + 前端 **5180**，Ctrl+C 同时停止 |

访问：

- 前端：http://127.0.0.1:5180
- API 文档：http://127.0.0.1:8000/docs
- 默认账号：`admin` / `admin123`

## 目录

| 目录 | 说明 |
|------|------|
| `backend/` | FastAPI API，SQLAlchemy 对齐 `../sql/supabase/01-init-schema.sql` |
| `frontend/` | React 前台开单 / 订单明细 / 报表 / 超管后台 |
| `setup-db.ps1` | 在 Supabase 上初始化 schema 与 admin |
| `start.ps1` | 一键启动脚本（Windows PowerShell） |
| `start.cmd` | 双击启动入口 |

## 手动启动

### 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 配置 .env 后
python -m scripts.apply_schema   # 首次
python -m scripts.init_admin
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```powershell
cd frontend
npm install
npm run dev
```

前端默认 http://127.0.0.1:5180 ，代理 `/api` → `8000`

## 角色落地页

| 角色 | 前端路由 |
|------|----------|
| CASHIER | `/floor` 开单 |
| MANAGER / ADMIN | `/admin` |
| SHAREHOLDER | `/reports` |

**页面路由**

| 路径 | 说明 |
|------|------|
| `/floor` | 前台开单 |
| `/orders` | 订单明细（股东不可见） |
| `/reports` | 日/周/月报表 + 导出 Excel |
| `/admin` | 超管：门店配置、台位、账号；经理：后台入口 |

**后台配置**（仅超级管理员 `ADMIN`）：http://127.0.0.1:5180/admin 或 `/config`  
含基准价、**计时自动计费**、权限开关、台位增删改。各页顶栏对管理员显示「后台配置」入口。

### 计时/自动计费

1. 后台 → 门店配置 → 开启「启用计时自动计费」
2. 设置单价（元/计费单位）、计费单位分钟数（默认 60=每小时）、最低计费单位数
3. 开单后开始计时，占用桌台显示已用时与预估金额；清台时按时长向上取整自动结算

计时字段已包含在 `sql/supabase/01-init-schema.sql` 中，无需额外迁移。

## 从 MySQL 迁移说明

原 `sql/01`～`03` 为 MySQL 脚本（历史保留）。当前版本使用 **Supabase PostgreSQL**，请使用 `sql/supabase/01-init-schema.sql`。
