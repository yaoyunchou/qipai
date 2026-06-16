# 棋牌室开单系统 · Supabase 数据库

后端通过 **SQLAlchemy 直连** Supabase PostgreSQL（`DATABASE_URL`），不使用 Supabase JS Client。

## 初始化

| 方式 | 说明 |
|------|------|
| **脚本（推荐）** | 在 `code/` 目录配置 `backend/.env` 后运行 `.\setup-db.ps1` |
| **SQL Editor** | 将 [01-init-schema.sql](01-init-schema.sql) 粘贴到 Supabase Dashboard → SQL Editor 执行，再 `python -m scripts.init_admin` |

## 连接串

在 Supabase Dashboard → **Project Settings → Database** 获取：

- **Transaction pooler**（推荐，端口 6543）：适合 FastAPI 服务端
- **Session pooler** 或 **Direct**（端口 5432）：长连接场景

写入 `code/backend/.env`：

```env
DATABASE_URL=postgresql+psycopg2://postgres.[ref]:[password]@...pooler.supabase.com:6543/postgres
DATABASE_SSL_MODE=require
```

## 表一览

与 MySQL 版一致，计时字段已合并进初始化脚本：

| 表名 | 用途 |
|------|------|
| `sys_user` | 账号；角色 CASHIER / MANAGER / SHAREHOLDER / ADMIN |
| `sys_store_config` | 单行全局配置：基准价、计时计费、权限开关 |
| `price_change_log` | 基准价修改审计 |
| `room_table` | 台位名称、排序、启用/停用 |
| `biz_order` | 开单订单：快照基准价、实收价、开单/清台人与时间、OPEN/CLOSED |

## 安全

- 所有业务表已 **启用 RLS** 且无公开策略，避免通过 Supabase Data API 被匿名访问。
- 后端使用数据库密码直连（`postgres` 角色），不受 RLS 限制。
- **切勿**将 `service_role` key 或数据库密码提交到 Git。

## 历史 MySQL 脚本

`../01-create-database-qipai.sql`、`../02-init-tables.sql`、`../03-add-timing-billing.sql` 为旧版 MySQL 脚本，仅作对照保留。
