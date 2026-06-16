# 变更日志

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
