# 变更日志

## 2026-11-16（生产发布）

### 生产发布：陪玩记账 + 借钱还钱 + 生活支出 + 移动端修复

- **版本**：`84e7c3c` → 已上线 https://jd.jxfg.top/qipai/
- **域名说明**：`jd.jxfg.top`（主）、`www.jxfg.top`、`jb.jxfgg.com` 三个域名指向同一目录 `/www/wwwroot/jb.jxfgg.com/qipai/`，一次部署同时生效。
- **流程**：按新规范执行（开发分支 → 6 个语义化提交 → cherry-pick 到 main → push → `--check` → 备份 → 部署 → 验证）。
- **新增功能**：陪玩记账（金额支持输赢）、借钱还钱（一人一账 + 点进去看流水）、报销「生活支出」分类、移动端 `¥` 输入框修复、运营数据重置纳入陪玩与借还。
- **数据库**：迁移 `05→11` 全部执行；新增 `loan_record`、`play_companion_record` 两表；`LIVING` 枚举已追加；陪玩金额非负约束已移除。
- **备份**：服务器 `/www/backup/qipai_20261116_113241/`，本地 `backups/prod_20261116_113148/`。
- **验证**：前端 200、SPA 子路由 200、新接口 401（已挂载需鉴权）、`health` ok、服务 RUNNING；业务数据无损失（订单 172、账号 5、报销 145、附件 103）。
- 详细记录见 [code/log.md](code/log.md)。

## 2026-11-16

### 借钱还钱：还钱入口统一弹框 + 手机端布局修复

- **两个「还钱」统一为弹框**：总账行尾的「还钱」原来会滚回顶部表单预填，与抽屉里的弹窗行为不一致；现在两处都打开同一个弹窗，默认金额取该客人未还余额。
- **修复 `¥` 输入框错位（影响全站）**：防 iOS 缩放的 `input{font-size:16px!important}` 把 antd 数字输入框内部撑歪，导致数字贴顶、与 `¥` 前缀不在一行；已补齐对齐规则，前缀与数字中线一致。
- **修复手机端输入框变扁**：移动端高度规则只写了 `.ant-input-number`，而带 `¥` 前缀时外层是 `.ant-input-number-affix-wrapper`，没匹配上，输入框被压到约 30px；现已覆盖，手机上恢复 42px 触控高度。
- **抽屉手机适配**：宽度改为 `min(720px,100vw)` 全宽；顶部三格汇总从 `Descriptions` 改为可换行的卡片（原来窄屏会把金额压成竖排文字）；流水表手机上只留日期/类型/金额，无需横向滚动。
- **主表格手机适配**：客人总账表手机上只留「客人/未还余额/操作」三列，点客人名即可看明细；页面边距由 24 收紧为 12。375px 下整页无横向溢出。
- 验证：模拟 iPhone 375×812 逐项测量（对齐、宽度、是否横向滚动）全部通过；类型检查与生产构建通过。

### 借钱还钱改为「一人一账 + 点进去看流水」

- 「借钱还钱」的默认视图由「所有人混在一起的流水表」改为 **「客人总账」**：一位客人一行，看借出合计、已还合计、未还余额、笔数和最近一次；原流水表下移为「全部流水」Tab，仍可按客人搜索。
- 客人名可点，或点行尾「明细」，打开**客人总账抽屉**：顶部三格汇总，下方该客人全部流水（日期、借出/还钱标签、带符号金额、备注、录入时间）按日期倒序；右上角在有欠款时提供「还钱」，默认金额就是当前未还余额。
- **核销口径**：确定按客人汇总，不做逐笔核销。借 100 + 借 200 后还 300，一条 `-300` 即结清，收银员不用关心抵哪笔——符合「客人只说我一共欠多少」的实际场景。
- 抽屉内余额与流水按**全部历史**计算，不受页面日期筛选影响，避免「上月借、本月还」算错。
- 接口：新增 `GET /api/v1/loans/borrowers/detail?borrower=<姓名>`（精确匹配），返回汇总 + 该客人全部流水；股东同样可读。
- 验证：接口层借 100+200→余额 300、再还 300→余额 0 均正确；浏览器实测总账→抽屉→还款弹窗（默认带出 644.00）链路正常；类型检查与生产构建通过。

### 借还明细行支持一键「还钱」

- 「借钱还钱」的「借还明细」表，每行**借出**记录的操作列新增「还钱」，与编辑、删除并列（操作列宽 130 → 190）。还钱行不重复给入口。
- 点击弹出小窗：客人锁定为该行客人，还款日期默认今天，**金额默认该行借出金额**，改个数即可保存；保存后新增一条 `-¥` 还款流水，余额按客人汇总抵扣。
- 沿用现有模型（还款是独立记录、按客人聚合），不做逐笔核销——弹窗内已写明这一点，避免误解。
- 验证：类型检查与生产构建通过；浏览器实测借出 ¥11 → 行内「还钱」→ 默认 11.00 → 改 5 保存 → 已还 5.00、余额 6.00、笔数 2 联动正确；测试数据已清理。

## 2026-11-15

### 借钱还钱独立菜单

- **背景**：客人有时需要向店里借钱、之后还钱，这类流水不属于台位订单、报销或陪玩，需要独立菜单与独立表格记录。
- **权限**：收银员 / 经理 / 超管可录入与查看明细，改删限本人（超管不限）；股东只能看汇总与客人欠款余额。
- **金额语义**：`loan_record.amount` 带符号——正数为借出（客人欠款），负数为还钱；按客人求和即为未还余额。
- **页面**：新增 `/loans`，导航「借钱还钱」。上半部分录入表单（日期、客人、联系方式、借出/还钱、金额、备注），下半部分日期区间筛选 + 借出/已还/未还余额三张汇总卡；两个 Tab：借还明细、客人欠款（按客人聚合，支持「只看还欠着」，并可一键带出「还钱」）。
- **接口**：`GET/POST /api/v1/loans`、`PUT/DELETE /api/v1/loans/{id}`、`GET /api/v1/loans/summary`、`GET /api/v1/loans/borrowers`。
- **数据库**：`sql/supabase/11-loan-record.sql` 新增 `loan_record` 表；迁移 `python -m scripts.apply_loan_record`，已接入 `setup-local-db.ps1`、`deploy.sh`、`DEPLOY.md`、`scripts/sync_prod_to_dev.py`。
- **超管「运营数据重置」** 一并清理借还记录，返回新增 `deleted_loan_records`。
- **验证**：接口冒烟 21 项通过；浏览器实测录入借出/还钱、一键还钱、编辑、删除、汇总与欠款聚合联动正常，手机端布局正常，测试数据已清理；`tsc --noEmit`、`npm run build` 通过。
- 详细改动见 [code/log.md](code/log.md)。

### 陪玩金额支持输赢（可为负数）

- **背景**：陪玩既可能赢也可能输，原实现三层都只允许非负（前端 `min={0}`、Schema `ge=0`、数据库 `CHECK (amount >= 0)`），输了记不上，也无法汇总输赢。
- **金额语义**：`play_companion_record.amount` 改为带符号——正数为赢，负数为输。历史非负数据语义不变，无需迁移。
- **录入交互**：不要求手敲负号，改为「输赢」切换（赢 / 输）+ 只收正数的金额框，提交时按方向加符号；默认「赢」，金额必须大于 0。
- **展示**：明细金额显示 `+¥80.50` / `-¥80.50`，赢绿输红；汇总拆成「赢合计 / 输合计 / 净额」三张卡，保留记录笔数与合计时长。
- **数据库**：`sql/supabase/10-play-companion-signed-amount.sql` 移除 `amount >= 0` 约束；执行脚本 `python -m scripts.apply_play_companion_signed_amount`。
- **接口**：`GET /api/v1/play-companion/summary` 返回字段由 `amount_total` 改为 `win_total` / `lose_total` / `net_total`。
- **验证**：接口冒烟 6 项 + 浏览器实测录入「输」「赢」、编辑回填与翻转、删除、汇总联动全部通过；`tsc --noEmit`、`npm run build` 通过。
- 详细改动见 [code/log.md](code/log.md)。

### 陪玩记账独立模块

- **背景**：客人不够人时需要安排陪玩，陪玩相关的账目单独成账，不与台位订单、报销混在一起。
- **权限**：收银员 / 经理 / 超管可录入、查看明细、修改删除自己的记录（超管可改删全部）；股东只能看汇总。
- **字段**：日期（必填）、台位（可不选，保存名称快照）、时长（小时）、金额（必填）、备注。不做审批流，保存即生效。
- **页面**：新增 `/play-companion`，导航「陪玩记账」。上半部分录入表单，下半部分按日期区间筛选的明细表 + 记录笔数/合计金额/合计时长三张汇总卡。
- **接口**：`GET/POST /api/v1/play-companion`、`PUT/DELETE /api/v1/play-companion/{id}`、`GET /api/v1/play-companion/summary`。
- **数据库**：`sql/supabase/09-play-companion.sql` 新增 `play_companion_record` 表（含 `play_date`、`table_id`、`table_name` 快照、`duration_hours`、`amount`、`remark`、`created_by`），带日期与录入人索引、`updated_at` 触发器；台位删除时 `table_id` 置 NULL 但名称快照保留。
- **超管「运营数据重置」** 一并清理陪玩记录，返回新增 `deleted_play_companion` 字段。
- **迁移**：`python -m scripts.apply_play_companion`；已接入 `setup-local-db.ps1`、`deploy.sh`、`DEPLOY.md`、`sync_prod_to_dev.py`。
- **验证**：本地库建表成功；接口冒烟 11 项通过（超管/经理可建、股东列表与创建均 403、股东汇总可读、非本人编辑 403、负数金额 422、增删改查与汇总联动正确）；浏览器实测录入带台位/不带台位各一条、编辑回填、删除刷新，汇总同步正确，未改任何账号密码；`tsc --noEmit` 与 `npm run build` 均通过。

### 报销分类新增「生活支出」

- 报销分类枚举增加 `LIVING`（生活支出），与固定/营运/沙箱支出并列；新建、编辑重提、列表、报表、Excel 导出均生效。
- 迁移：`sql/supabase/08-expense-category-living.sql` + `python -m scripts.apply_expense_category_living`。
- 详细改动见 [code/log.md](code/log.md)。

## 2026-07-03

### 首次生产环境部署（腾讯云 + 宝塔面板）

- 新增 `DEPLOY.md`：宝塔面板部署文档（服务器信息、PostgreSQL 方案、Nginx/Supervisor 配置、上线验证清单）。
- 新增 `deploy.sh`：一键部署脚本（备份 → 拉代码 → 配置 `.env` → 装依赖/建库 → 建前端 → 提示手动步骤）。
- 排查生产服务器 SSH 无法连接问题：确认是宝塔防火墙屏蔽 22 端口 + SSH 仅允许 `gssapi` 认证导致，非安全组或密码问题。
- 股东（SHAREHOLDER）权限调整随本次上线一并发布：开放开台看板访问、可查看自己订单、取消前端强制跳转 `/reports`。

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
