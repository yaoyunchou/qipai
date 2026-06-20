# 变更日志

## 2026-06-19

### 确认 main 分支推送自动部署（Vercel Git 集成）

- 验证 `yaoyunchou/qipai` 已关联 Vercel 项目 `qipai`，生产分支为 `main`。
- 历史部署记录显示 `githubCommitRef: main` 且 `githubDeployment: 1`，推送 main 已自动触发生产构建。
- `code/README.md` 补充「自动部署（已配置）」说明。

## 2026-06-18

### 重新部署 Vercel 生产环境

- 执行 `npx vercel --prod --yes`，构建成功（前端 Vite + 后端 Python 3.12）。
- 生产地址：https://qipai-pearl.vercel.app（`/health`、`/floor` 均 200）。
- 部署详情：https://vercel.com/yaoyunchous-projects/qipai/3DTUhfrdLsPeqjtdYJqA2oghGAG6

### 按「先改这些」文档调整前台与后台

- **后台门店配置**：隐藏「启用计时自动计费」及相关计费单位字段，卡片标题改为「基准价与权限」；保存时强制 `enable_timing: false`。
- **前台桌台卡片**：占用桌台显示开台时间（HH:MM）、用时（HH:MM）及金额，样式与修改意见一致。
- **清台弹窗**：「实收金额」改为「原价」；改价提示改为「留空则按实收金额」；新增开台备注展示。
- **后端**：`TableBoardItem` 增加 `base_price`、`remark` 字段供清台弹窗使用。

## 2026-06-17

### 完成 Vercel 生产部署

- 仓库根目录新增 `vercel.json`、`pyproject.toml`、`api/index.py`、`scripts/vercel_build.py`，从根目录构建并指向 `code/`。
- `vercel.json` 增加 `buildCommand` 确保前端 `npm ci && vite build` 执行。
- 通过 Vercel CLI 配置 Production 环境变量：`DATABASE_URL`、`DATABASE_SSL_MODE`、`JWT_SECRET`。
- 生产地址：https://qipai-pearl.vercel.app（`/health` 200，`/floor` 前端可访问）。

### 仓库根目录增加 Vercel 部署配置

- **问题**：Vercel 从仓库根目录构建时找不到 `code/vercel.json`，部署为空壳（404）。
- **修复**：在仓库根添加 `vercel.json`、`pyproject.toml`、`api/index.py`、`scripts/vercel_build.py`，路径指向 `code/frontend` 与 `code/backend`，无需在控制台改 Root Directory。

### 修复 start.ps1 在 Windows PowerShell 5.1 下语法报错

- **现象**：双击 `start.cmd` 报 `MissingEndCurlyBrace`、中文乱码导致字符串未闭合。
- **原因**：`start.ps1` 为 UTF-8 无 BOM，中文 Windows 默认按 GBK 解析脚本。
- **修复**：以 UTF-8 BOM 保存；提示语中 `1)` 改为单引号字符串避免误解析。

### 修复开单/清台弹窗确认按钮可重复点击

- **现象**：开单 Modal 点「确定」后接口返回前可多次提交。
- **修复**：`Floor.tsx` 增加 `openSubmitting` / `closeSubmitting`，Modal 使用 `confirmLoading` 并在提交中禁用取消与遮罩关闭。

### 修复 backend 启动 NameError: date 未定义

- **现象**：uvicorn 启动失败，`orders.py` 报 `NameError: name 'date' is not defined`。
- **修复**：`orders.py` 补充 `from datetime import date`。

### 修复 Supabase 初始化 SQL 首次执行失败

- **现象**：在 SQL Editor 执行 `01-init-schema.sql` 报错 `42P01: relation "biz_order" does not exist`。
- **原因**：删表前先 `DROP TRIGGER ... ON biz_order`，首次建库时表尚不存在，PostgreSQL 仍会报错（`DROP TRIGGER IF EXISTS` 不跳过「表不存在」）。
- **修复**：移除多余的 `DROP TRIGGER`，仅保留 `DROP TABLE IF EXISTS biz_order CASCADE`（CASCADE 会一并删除触发器）。

## 2026-06-11

### 修复 localhost:5180 白屏/报错

- **现象**：访问 http://localhost:5180/ 页面空白，Vite 对 `Admin.tsx` 返回 500。
- **原因**：`frontend/src/pages/Admin.tsx` 第 63 行 `useEffect(() {` 缺少箭头 `=>`，语法错误导致整包编译失败（`App.tsx` 静态 import 了 Admin 页面）。
- **修复**：改为 `useEffect(() => {`。
- **验证**：刷新后正常跳转到登录页，用户名/密码表单可显示。

### 补齐 PRD 未完成功能

**后端**

- 新增 `GET/POST/PATCH/DELETE /api/v1/users`（超管账号 CRUD）
- 新增 `GET /api/v1/reports/export`（Excel 导出，股东仅汇总 sheet）
- 订单列表 `GET /api/v1/orders` 增加 `start`/`end` 日期筛选
- 依赖增加 `openpyxl`

**前端**

- 新增 `/orders` 订单明细页（状态/日期筛选；收银员仅本人，经理/超管全店）
- 报表页：日期选择器 + 导出 Excel（按角色与 `cashier_allow_export` 控制）
- 开单弹窗：备注输入（选填）
- 后台台位：编辑名称/排序
- 后台新增「账号管理」Tab：新建、启停、重置密码、删除
- 顶栏增加「订单」入口

**仍未做（非本期代码范围）**

- 公网云部署、HTTPS、移动端专项优化
