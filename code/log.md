# 变更日志

## 2026-11-16（hotfix）

### 陪玩 / 借还：删除仅管理员，输赢与借还开关加颜色

分支：`hotfix/admin-delete-and-switch-color`（从 `main` 的 `e96521e` 拉出）

**验证（2026-11-16）**
- 经理录入陪玩「输 -2.50」成功，改成「赢 3.00」成功，自己删除返回 403「只有管理员可以删除陪玩记录」，管理员删除成功。
- 经理录入借钱 6.00、还钱 -6.00 成功，自己可改，管理员可改他人记录；经理删除返回 403，股东删除返回 403，管理员删除成功。测试数据已清掉。
- 页面实测：借钱选中底色 `#1677ff`、还钱选中底色 `#cf1322`；赢选中底色 `#cf1322`、输选中底色 `#1677ff`，选中文字为白色。新增表单和编辑弹窗一致。管理员在流水里仍能看到「删除」。

**删除权限**
- 陪玩记账、借钱还钱的删除改为只有管理员可以操作。收银员、经理即使是自己录入的，录错了也不能删除；页面上不再显示「删除」。
- 编辑仍按原规则：本人可改自己的记录，管理员可改全部。股东仍然只能看汇总。
- 后端 `DELETE` 对非管理员直接返回 403（「只有管理员可以删除…」），不依赖前端隐藏按钮。

**开关颜色**
- 新增 `DirectionSwitch`：选中项整块变色，未选中文字也带对应颜色。
- 借钱 = 蓝（`#1677ff`），还钱 = 红（`#cf1322`）。录入表单上的「借出」文案改为「借钱」，与开关叫法一致；列表标签仍是「借出 / 还钱」。
- 输 = 蓝，赢 = 红。新增和编辑弹窗都用同一套开关。
- 「只看还欠着 / 全部客人」筛选开关不在这次改色范围内。

## 2026-11-16（生产发布）

### 生产环境发布：陪玩记账 + 借钱还钱 + 生活支出 + 移动端修复

**发布版本**：`84e7c3c`（main，已推送 origin）
**发布地址**：https://jd.jxfg.top/qipai/（主域名）
**其它域名**：`www.jxfg.top`、`jb.jxfgg.com` 指向同一目录，同时生效
**流程**：按新规范执行——开发分支 → 拆分为 6 个语义化提交 → cherry-pick 到 main → push → `--check` 校验 → 备份 → 部署 → 验证

**本次新增到线上的功能**：
1. 陪玩记账模块（`/play-companion`）：金额支持输赢（正=赢/负=输），汇总拆为赢合计/输合计/净额
2. 借钱还钱模块（`/loans`）：一人一账，点客人进抽屉看全部流水；两个「还钱」入口统一为弹框
3. 报销新增「生活支出」分类（`LIVING` 枚举）
4. 移动端修复：全站 `¥` 数字输入框错位/高度问题、借还页抽屉与表格适配
5. 运营数据重置纳入陪玩与借还记录

**备份**：
- 服务器：`/www/backup/qipai_20261116_113241/db/qipai_20261116_113241.dump`（53 KB）
- 本地：`backups/prod_20261116_113148/`（SQL + 107 个附件）

**数据库迁移**（全部幂等，先迁移后上传代码）：
`05 → 06 → 07 → 08 → 09 → 10 → 11`

**验证结果**：
- 前端主页 200（418 B）、JS 200（1,470,963 B）、SPA 子路由 `/qipai/loans` 与 `/qipai/play-companion` 均 200
- 登录接口 401（正常响应）；`loans/summary`、`loans/borrowers`、`play-companion/summary` 均 401（接口已挂载且需鉴权）
- 新表 `loan_record`、`play_companion_record` 已创建（各 0 条）；`LIVING` 枚举已追加；`chk_play_companion_amount` 约束已移除
- **业务数据完好**：`biz_order` 172、`sys_user` 5、`expense_claim` 145、`expense_claim_attachment` 103（与部署前一致）
- `qipai-api` RUNNING

**部署中发现并修正的问题**：
- 部署脚本原用 `http://127.0.0.1/qipai/` 检测前端，但该站点强制跳 HTTPS，curl 不跟随重定向 → 误报 `frontend:404`。已改为 `curl -skL` + HTTPS + `Host` 头，并新增 SPA 子路由与新接口的存在性检测（`new_api_*` 应为 401，404 表示未挂载）。
- **域名纠正**：生产实际有三个域名指向同一目录，主域名为 `jd.jxfg.top`（证书至 2027-01-04），`jb.jxfgg.com` 为旧域名（证书 2026-12-07 到期）。部署脚本原先硬编码只提示旧域名，且只验证旧域名。现已抽出 `PRIMARY_DOMAIN` / `KNOWN_DOMAINS` / `FRONTEND_ROOT` 常量，前端目录路径保持实际路径不变，验证改为逐个域名检测。
- 核查线上真实状态时发现：线上代码长期为手工上传，`git` 记录的版本号与实际功能不一致（附件文件存储、报销作废其实早已上线）。本次部署前已逐项核实，避免重复判断上线范围。

**线上此前已存在（本次仅同步代码）**：报销附件文件存储、报销作废、股东开台/订单权限。

## 2026-11-16

### 新增发布流程规范 + 部署强制校验

- **背景**：此前 `scripts/deploy_prod.py` 可从任意工作区直接部署，存在「在开发分支改了代码直接上线」「工作区有未提交改动就发布」「本地代码与远端 main 不一致」等风险，线上版本无法追溯。
- **新增强制校验**（`verify_release_ready`，部署前置执行，任一不满足直接中止并打印修复指引）：
  1. 当前分支必须是 `main`（可用 `--release-branch` 指定，默认 main）
  2. 工作区必须干净（无未提交改动、无未跟踪文件，`--allow-dirty` 可跳过但不推荐）
  3. 本地分支必须与上游完全一致（未 push 或落后都会中止）
  4. `HEAD` 必须等于 `origin/main`（确保代码已合并进主分支）
- **新增 `--check` 模式**：只做校验、不执行任何部署动作，用于上线前 dry-run。
- **新增 [RELEASE.md](RELEASE.md)**：写明铁律（只从 main 部署 / 必须已合并 / 必须已推送 / 必须无差异 / 先迁移后上线）、标准 5 步流程（开发 → `merge --no-ff` → push → `--check` → 部署）、禁止事项对照表、代码/数据库/前端三类回滚步骤、迁移幂等约定、分支命名规范。
- **脚本其它改进**：迁移列表补全至 `11-loan-record.sql`（原先只到 `07`，会导致新代码引用不存在的表）；执行顺序由「先上传代码后迁移」调整为**先迁移、迁移失败即中止且不动线上代码**。
- **验证**：在当前开发分支执行 `--check`，正确识别并中止了三类问题（分支不符、工作区 2 个未提交改动、HEAD `43cffc4` ≠ origin/main `f4cae08`），退出码 1，未触发任何部署动作。
- **`.gitignore` 补充**：排除 `code/mp-weixin/`（微信小程序，9.1 MB / 3058 文件，与网页版无关）、`.vscode/`、`**/__pycache__/`。

## 2026-11-16（早前）

### 借钱还钱：两个「还钱」入口统一为弹框 + 移动端适配

- **统一弹框**：原来「客人总账」行尾的「还钱」是滚回顶部表单预填，抽屉里的才是弹窗，交互不一致。现在两处都走同一个 `Modal`（`repayTarget` 轻量状态：客人 + 联系方式 + 默认金额 + 提示文案）。默认金额：行尾按钮取该客人**未还余额**，抽屉按钮同样取余额，明细行的「还钱」取该行借出金额。
- **修复输入框错位（全站）**：`index.css` 为防 iOS 聚焦缩放写了 `input { font-size: 16px !important }`，把 antd `InputNumber` 内部 input 撑成 33px 并贴顶，与 `¥` 前缀错位，弹窗里尤其明显。补三条规则：`.ant-input-number-affix-wrapper{display:inline-flex;align-items:center}`、内部 `.ant-input-number` 撑满高度且去边框透明底、`input-wrap`/`input` 高度 100%。修复后前缀、输入区、容器中线完全一致（实测 375px 下三者中心线同为 398）。
- **修复移动端输入框高度**：`@media (max-width:767px)` 里原来只写了 `.ant-input-number{height:42px}`，但**带 `¥` 前缀时外层是 `.ant-input-number-affix-wrapper`，压根没匹配上**，导致手机上该输入框没有固定高度、被压成 29~31px 的扁平盒子。现已把 `.ant-input-number-affix-wrapper` 加入高度规则并让内部撑满。
- **抽屉移动端适配**：
  - 宽度由 `720` 改为 `min(720px, 100vw)`，手机上全宽。
  - 顶部三格汇总从 `Descriptions`（窄屏会把「借出合计 ¥944.00」压成竖排文字）改为 `Flex` + `Statistic` 卡片，`min-width:130px` 自动换行：375px 下前两张并排、余额卡独占一行，无挤压。
  - 流水表在手机上只保留「日期 / 类型 / 金额」三列（去掉备注、录入时间），日期格式简化为 `MM-DD`，`scroll` 仅桌面端启用 → 375px 下 `scrollWidth === clientWidth`，无横向滚动。
- **主表格移动端适配**：客人总账表在手机上只保留「客人 / 未还余额 / 操作」三列（隐藏借出合计、已还合计、笔数、最近一次），操作列手机上只留「还钱」（点客人名即可看明细），`scroll` 仅桌面端启用 → 375px 下无横向滚动。「全部流水」9 列保留横向滚动（信息密度需要）。
- **页面边距**：手机上 `Content` padding 由 24 收紧为 12，桌面端不变。
- **验证**（模拟 iPhone 375×812）：输入框 42px 高、`¥`/数字/容器中线均为 398；抽屉全宽 375px、三张汇总卡 134/134/301 自动换行、流水表无横向滚动；主表格三列无横向滚动（`scrollWidth=clientWidth=277`）；`bodyScrollWidth === innerWidth` 确认整页无横向溢出。`tsc --noEmit` 与 `npm run build` 通过。

## 2026-11-16（早前）

### 借钱还钱改为「一人一账 + 点进去看流水」

- **背景**：原来「借还明细」把所有人的流水混在一张表里，收银员看某位客人时得先搜名字，看到的是夹杂他人的流水，且看不到这个人一共借了几次、每次多少。按「借 100、再借 200、还 300」这种真实场景，需要的是**按客人看总账，点进去看这个人每笔流水**。
- **核销方式**：确定采用**按客人汇总**（一人一账），不做逐笔核销。还款是独立流水、按客人姓名汇总抵扣，所以「借 100 + 借 200、还 300」一条 `-300` 记录即结清，收银员不用关心抵哪笔。理由：棋牌室借钱是口头的，客人只说「我一共欠多少」，强行 FIFO 核销在客人只想抵部分时无法纠正。
- **主视图调换**：默认 Tab 由「借还明细」改为 **「客人总账」**（一人一行：客人、借出合计、已还合计、未还余额、笔数、最近一次），原流水表降为第二个 Tab **「全部流水」**，仍保留按客人搜索。
- **客人名可点**：总账表的客人名做成链接，点击直接打开该客人详情，不必再找「明细」按钮。
- **新增详情抽屉**（`Drawer`，宽 720）：
  - 标题「客人总账 · 客人名」，右上角在仍有欠款时提供「还钱」主按钮（默认金额 = 当前未还余额）；
  - 顶部三格汇总（借出合计 / 已还合计 / 未还余额），沿用红借出、绿还款配色；
  - 下方该客人的**全部流水**（日期、类型标签、带符号金额、备注、录入时间），按日期倒序。
- **余额口径**：详情接口的汇总与流水**按全部历史计算，不受页面日期筛选影响**，否则「上月借、本月还」会被算错——抽屉内有文案说明。
- **接口**：新增 `GET /api/v1/loans/borrowers/detail?borrower=<姓名>`（精确匹配，`borrower == name`，避免「001」与「0012」串账），返回 `lent_total` / `repaid_total` / `balance` / `record_count` / `last_date` / `records`。Schema 新增 `LoanBorrowerDetailOut`。股东同样可读。
- **联动刷新**：在抽屉内还款、或在抽屉外删除记录后，抽屉与列表都会重新拉取，余额即时更新。
- **重构**：还款弹窗的目标由「某条完整记录」改为轻量的 `repayTarget`（客人 + 联系方式 + 默认金额 + 提示文案），使得「明细行还钱」与「总账还钱」共用同一弹窗，不再需要伪造记录对象。
- **验证**：
  - 接口验证：借 100 + 借 200 → `lent=300 / balance=300 / count=2`；再还 300 → `repaid=300 / balance=0 / count=3`，与预期一致；精确匹配校验（另建 `__测试客人__2` 不污染 `__测试客人__` 的笔数）。
  - 浏览器实测：「客人总账」Tab 显示 001 一行（借出 944 / 已还 300 / 欠 644 / 3 笔）→ 点「明细」抽屉标题「客人总账 · 001」、三格汇总与三笔流水倒序正确 → 抽屉右上「还钱」弹窗金额自动带出 `644.00`、文案为「当前未还余额 ¥644.00」。
  - 我造的测试数据已清理；未改动你手动录入的「001」三条记录。
  - `tsc --noEmit` 与 `npm run build` 通过（exit 0）。

## 2026-11-16（早前）

### 借还明细行新增「还钱」快捷入口

- **背景**：原有「还钱」只存在于「客人欠款」Tab（对仍欠款的客人），对着具体某笔借出记录时没法直接还款，收银员要自己切 Tab 再找客人。
- **交互**：`借还明细` 每一行**借出**记录的「操作」列新增「还钱」，位次为「还钱 / 编辑 / 删除」（操作列宽 130 → 190）。点击弹出「记录还钱 · 客人名」小窗，客人锁定为该行客人，**还钱日期默认今天、金额默认该行借出金额**，改个数即可保存。
- **只在借出行显示**：还钱记录行不再重复给入口（金额 > 0 才渲染，还钱行只有编辑 / 删除）。
- **保存行为**：弹窗里填的金额以 `-Math.abs(amount)` 作为新记录 POST 到 `/api/v1/loans`，`borrower` / `contact` 沿用该行，备注可填。本质是新增一条该客人的还款流水，余额仍按客人汇总抵扣（沿用现有模型，不做逐笔核销）。
- **弹窗说明文案**：明确提示「这笔借出 ¥11.00（日期）。还款会作为一条独立记录计入「客人」名下，余额按客人汇总抵扣」，避免误解为针对该笔核销。
- **权限沿用**：非本人录入且非超管的记录操作列仍显示 `-`，看不到「还钱」。
- **验证**：`tsc --noEmit` 与 `npm run build` 通过（exit 0）；浏览器实测——借出 ¥11 的行出现「还钱」→ 点开弹窗标题「记录还钱 · 33」、金额默认 `11.00` → 改为 5 保存 → 明细新增 `-¥5.00` 还钱行、已还合计 5.00、未还余额 11.00 → 6.00、笔数 2，「客人欠款」Tab 同步；还钱行操作列确认无「还钱」按钮；测试数据（2 条）已清理，`loan_record` 现有 0 条。

## 2026-11-15

### 借钱还钱独立模块（新菜单 + 独立表）

- **背景**：客人有时会临时向店里借钱、之后再还钱，这类流水既不属于台位订单，也不属于报销与陪玩，需要单独一页记录并能一眼看出「谁还欠多少」。
- **权限**：`CASHIER` / `MANAGER` / `ADMIN` 可录入、看明细、改删（非超管只能改删自己录入的记录）；`SHAREHOLDER` 只读——可看汇总与客人欠款聚合，看不到明细、也录不进。
- **金额语义**：沿用本项目「带符号金额」的既有做法，`loan_record.amount` **正数为借出**（客人欠店里）、**负数为还钱**（客人还款）。这样一笔流水就是一条记录，按客人 `SUM` 即得未还余额，不用再建还款子表。
- **字段**：日期（必填）、客人（必填，存客人姓名/称呼）、联系方式（选填）、金额（必填，> 0，方向另选）、备注。不做审批流，保存即生效。
- **录入交互**：不手敲负号，改为「类型」`Segmented`（借出 / 还钱）+ 只收正数的金额框，提交时按方向加符号（`toSignedAmount`）；默认「借出」，保存后重置回「借出」。
- **页面** `/loans`，导航「借钱还钱」（桌面顶栏与移动端折叠菜单都会出现）：
  - 上半部分「新增借还记录」表单；
  - 下半部分按日期区间筛选，四张汇总卡：**记录笔数 / 借出合计 / 已还合计 / 未还余额（借出 - 已还）**；
  - 两个 Tab：**借还明细**（日期、客人、联系方式、类型标签、带符号金额、备注、录入人、录入时间、操作，支持按客人搜索）与 **客人欠款**（按客人聚合借出/已还/余额/笔数/最近一次，可切「只看还欠着 / 全部客人」）。
- **一键还钱**：「客人欠款」里对仍有余额的客人提供「还钱」按钮，直接带出客人姓名、切到「还钱」并把余额填进金额框，收银员改个数就能保存。
- **展示**：借出 `+¥500.00` 红色（`#cf1322`）、还钱 `-¥300.00` 绿色（`#3f8600`）、右对齐；余额列显示「欠 ¥200.00」/「多还 ¥50.00」/「已结清」。
- **接口**：`GET/POST /api/v1/loans`、`PUT/DELETE /api/v1/loans/{id}`、`GET /api/v1/loans/summary`（借出/已还/余额聚合）、`GET /api/v1/loans/borrowers`（按客人聚合，支持 `only_pending`）。
- **数据库**：新增 `sql/supabase/11-loan-record.sql` 建 `loan_record` 表（`loan_date`、`borrower`、`contact`、`amount`、`remark`、`created_by`、时间戳），带日期/客人/录入人索引、`updated_at` 触发器、`amount <> 0` 与非空客人校验，并启用 RLS。执行脚本 `python -m scripts.apply_loan_record`。
- **超管「运营数据重置」** 一并清理借还记录，`TRUNCATE` 列表加入 `loan_record`，返回新增 `deleted_loan_records`；前端提示文案同步。
- **迁移/部署串联**：`setup-local-db.ps1`、`deploy.sh`、`DEPLOY.md`、`scripts/sync_prod_to_dev.py`（增量迁移列表 + `fix_sequences` 表列表）全部加入 `11-loan-record.sql`。
- **验证**：
  - 接口冒烟 **21 项全通过**：超管/经理可录入借出与还钱（负数）、金额 0 与空白客人被 422 拒绝、汇总（500 / 200 / 300）与客人欠款聚合（余额 300、笔数 2）正确、按客人筛选、编辑还款额后余额联动为 250、股东可看汇总与客人欠款但看明细与录入均 403、经理改他人记录 403 而改自己的 200、删除后汇总归零、未登录 401/403。
  - 浏览器实测（临时收银账号，未改动任何现有账号密码）：录入借出 `+¥500.00` → 汇总借出 500、余额 500；「客人欠款」出现 1 位欠款客人 → 点「还钱」自动带出客人与 500 并切到「还钱」→ 保存后明细出现 `-¥500.00`、已还 500、余额归 0、欠款列表自动清空；编辑该笔为 300 后余额变 200、欠款列表恢复并显示「欠 ¥200.00」；删除后汇总同步回落；手机尺寸下表单与表格布局正常。
  - 实测数据已清理（`loan_record` 归零、临时账号已删）；`tsc --noEmit` 与 `npm run build` 均通过。
- **线上需执行一次** `python -m scripts.apply_loan_record`，并重新构建上传前端。

### 陪玩金额支持输赢（可为负数）

- **背景**：陪玩既有赢也有输，原实现三层都只允许非负（前端 `min={0}`、Schema `ge=0`、数据库 `CHECK (amount >= 0)`），输了记不上，也无法汇总赢输。
- **金额语义**：`play_companion_record.amount` 改为带符号——正数为赢（进账），负数为输（支出）。历史非负数据无需迁移，语义不变。
- **录入交互**：不让人手敲负号，改为「输赢」`Segmented`（赢 / 输）+ 只收正数的金额框，提交时按方向加符号（`toSignedAmount`）。默认「赢」，保存后重置回「赢」。金额必须 > 0，0 在前端和后端都拒绝。
- **明细展示**：金额列统一显示 `+¥80.00` / `-¥80.50`，赢为绿（`#3f8600`）、输为红（`#cf1322`）、右对齐。
- **汇总口径**：原来单张「合计金额」拆为 **赢合计 / 输合计 / 净额（赢 - 输）** 三张卡（输合计以正数展示输了多少钱，净额可为负并标红），保留记录笔数与合计时长。接口返回字段由 `amount_total` 改为 `win_total` / `lose_total` / `net_total`。
- **编辑回填**：按 `amount` 正负自动还原成「赢/输」+ 绝对值，改方向后保存即翻转符号。
- **后端**：`schemas/play_companion.py` 抽出 `PlayCompanionBase`，`amount` 改为 `ge=-99999999.99 / le=99999999.99`（对齐 `NUMERIC(10,2)`）并加 `field_validator` 拒绝 0；`api/v1/play_companion.py` 的 summary 用 `case()` 分别聚合赢、输与净额。
- **数据库**：新增迁移 `sql/supabase/10-play-companion-signed-amount.sql`（`DROP CONSTRAINT IF EXISTS chk_play_companion_amount` + 列注释），执行脚本 `python -m scripts.apply_play_companion_signed_amount`；已接入 `setup-local-db.ps1`、`deploy.sh`、`DEPLOY.md`、`scripts/sync_prod_to_dev.py` 增量迁移列表与 `README.md` 说明。
- **验证**：Schema 单测（负/正可入、0 与超范围被拒）通过；库内负数落库成功、约束已移除、赢/输/净额聚合正确（120 / 80.5 / 39.5）；接口冒烟 6 项通过（输 -80.5、赢 120、0 返回 422、汇总正确、编辑转正、删除）；用临时超管账号浏览器实测切「输」录入 → 明细 `-¥80.50`、汇总输合计 `-¥80.50`、净额 `-¥80.50`；编辑回填选中「输」→ 改「赢」保存后明细 `+¥80.50`、汇总同步；随后删除记录、清理临时账号（未改动任何现有账号密码）；`tsc --noEmit` 与 `npm run build` 均通过。
- **线上需执行一次** `python -m scripts.apply_play_companion_signed_amount`，并重新构建上传前端。

### 陪玩记账独立模块上线

- 新增独立页面 `/play-companion`（导航「陪玩记账」）：日期 + 台位（可选）+ 时长 + 金额 + 备注，保存即生效，不走审批
- 新增 `backend/app/models/play_companion.py`、`schemas/play_companion.py`、`api/v1/play_companion.py`；`router.py` 挂载 `/api/v1/play-companion`
- 权限：`CASHIER`/`MANAGER`/`ADMIN` 可录入与查看明细，非超管只能改删自己的记录；`SHAREHOLDER` 仅可读 `summary`
- 新增 `sql/supabase/09-play-companion.sql` 与 `python -m scripts.apply_play_companion`
- 表 `play_companion_record` 保存 `table_name` 快照，台位删除后历史记录仍可读
- 超管「运营数据重置」（`/api/v1/orders/reset-operations`）纳入陪玩记录，返回 `deleted_play_companion`
- `setup-local-db.ps1`、`deploy.sh`、`DEPLOY.md`、`scripts/sync_prod_to_dev.py` 同步加入新迁移
- 验证：接口冒烟 11 项全通过；浏览器实测录入/编辑/删除/汇总联动正常；`tsc --noEmit`、`npm run build` 通过

### 报销分类新增「生活支出」

- 报销分类新增「生活支出」（枚举值 `LIVING`），新建报销 / 编辑重提下拉、列表分类列、报表分类明细、Excel 导出（汇总 + 明细 + 全部报销）全部支持
- 数据库：新增迁移 `sql/supabase/08-expense-category-living.sql`（`ALTER TYPE expense_category ADD VALUE IF NOT EXISTS 'LIVING'`），执行脚本 `python -m scripts.apply_expense_category_living`
- 后端：`ExpenseCategory` 枚举增加 `LIVING`；`app/api/v1/expenses.py` 两处 `CATEGORY_LABEL` 与报表汇总分类遍历补 `LIVING`
- 前端：`pages/Expenses.tsx` 的 `CATEGORY_LABEL` / `CATEGORY_OPTIONS` 增加「生活支出」；`api/client.ts` 分类联合类型补 `"LIVING"`
- 部署/初始化脚本同步：`code/setup-local-db.ps1`、`deploy.sh` 首次初始化、`DEPLOY.md`、`scripts/sync_prod_to_dev.py` 增量迁移列表
- 验证：本地库枚举顺序为 `FIXED, OPERATIONS, SANDBOX, LIVING`；插入 `category='LIVING'` 报销单成功（已回滚）；`tsc --noEmit` 与 `npm run build` 均通过
- 线上需执行一次 `python -m scripts.apply_expense_category_living`，并重新构建上传前端

## 2026-10-10

- 商城后台 `admin` 无法通过忘记密码找回：库里是 bcrypt，已按 Yii `password_hash`（cost 13）重置 `zjhj_bd_user` 中 `id=1` 的密码。明文未写入日志

## 2026-10-09

- 去掉站点根目录被替换的「世博体育」首页：`/www/wwwroot/jb.jxfgg.com/index.php` 改为跳转到 `/web/index.php`。原文件和 8 月 17 日写入的 `controllers/mall/v2/` 已移到服务器 `/root/quarantine-20261009/`，不再对公网提供。访问 `https://jd.jxfg.top/` 现为 302，最终打开商城登录页「商城管理」

## 2026-10-07

- 手机 H5 的 `siteinfo.js`（mall 1、2）不再写死 `https://jb.jxfgg.com`，`apiroot` 改为 `location.origin + '/web/index.php?_mall_id=...'`。发布逻辑 `plugins/mobile/forms/mall/IndexForm.php` 同步为按当前域名生成，避免下次发布又写死。这样从 `jd.jxfg.top` 打开 H5 时接口不再跨域请求旧域名
- 商城接口输出按当前访问域名替换本站历史域名：`core/WebApplication.php` 的 `str2url()` 在原有占位符替换之后，把 `jb.jxfgg.com`、`jd.jxfg.top`、`www.jxfg.top` 换成本次请求的 Host。未改数据库。用 `jd.jxfg.top` 请求 `r=api/index/index` 时，装修图地址已变为 `https://jd.jxfg.top/web/...`

## 2026-10-06

- 新域名站点 `www.jxfg.top`：Nginx 根目录与 `jb.jxfgg.com` 相同（`/www/wwwroot/jb.jxfgg.com`），含 PHP 商城与 `/qipai/`；Let's Encrypt 证书已签发并开启 HTTPS
- `jb.jxfg.top` 公网仍无解析；根域 `jxfg.top` 指向另一台机器 `183.238.171.233`，未挂到本站
- 新域名 `jd.jxfg.top`（A → `1.12.219.199`）：Nginx 与 `jb.jxfgg.com` 同根目录，已签发 HTTPS；商城 `/web/index.php` 与 `/qipai/` 均 200
- `jd.jxfg.top`、`www.jxfg.top` 证书由 ECC 改为 RSA（2048），`ssl_protocols` 改为 `TLSv1.2 TLSv1.3`，并开启 HTTP/2。登录页在服务器上返回 200（标题「商城管理」）。商城按当前 Host 生成地址，后台装修里的图片仍指向 `https://jb.jxfgg.com/...`，旧域名未下线前无需改库

## 2026-09-14

- **生产部署**（`https://jb.jxfgg.com/qipai/`）：开单开始时间手机端 `antd-mobile` 底部滚轮选择器（`OpenTimeInput`）
  - 线上备份：`/www/backup/qipai_20260914_114101/`
  - 前端已构建上传；`qipai-api` 已重启，`/health` 正常

## 2026-08-20

- **生产部署**（`https://jb.jxfgg.com/qipai/`）：网站标题「安牌」、订单页运营数据重置、开单可选开始时间、`opened_at` API、`fix_sequences` 脚本等
  - 线上备份：`/www/backup/qipai_20260820_092953/`
  - 前端 `vite build --base=/qipai/` 已上传；Supervisor 重启 `qipai-api`，`/health` 正常
- **开单开始时间移动端优化**：手机端使用 `antd-mobile` 底部抽屉滚轮选择器（`OpenTimeInput`）；PC 端仍用 Ant Design DatePicker

## 2026-08-18

- **本地开发改用 Docker PostgreSQL**：新增 `code/docker-compose.yml`（`postgres:15-alpine`，库 `qipai` / 用户 `qipai` / 密码 `qipai_local_dev`，端口 `5432`）
- 新增 `code/docker-db.ps1`（up/down/status/logs）、`code/setup-local-db.ps1`（一键启动容器 + schema + 报销迁移 + `init_admin`）
- 新增 `code/backend/.env.local.docker` 模板；`backend/.env` 已切换为本地连接（`DATABASE_SSL_MODE` 留空）
- 更新 `backend/.env.example`、`start.ps1` 提示文案，README 补充 Docker 本地库说明
- **生产数据同步到本地 Docker**：`backend\.venv\Scripts\python.exe ..\scripts\sync_prod_to_dev.py --yes`；导入 422 条 SQL，`expense_claim=86`，附件 107 个至 `backend/uploads/`
- 前端网站标题（浏览器 Tab）改为「安牌」（`frontend/index.html`）
- **订单明细页**：超管可见「运营数据重置」按钮；`POST /api/v1/orders/reset-operations` 清除订单、报销单及附件、基准价变更记录（保留账号/台位/门店配置/审批授权）
- **前台开单**：开单弹窗增加「开始时间」选择（默认当前时间，可修改）；`POST /api/v1/orders/open` 支持 `opened_at` 字段
- 修复生产数据同步后 `biz_order_pkey` 冲突：新增 `scripts/fix_sequences.py`，`sync_prod_to_dev` 恢复后自动对齐 id 序列（非开始时间字段问题）
- `.vscode/launch.json`：新增 FastAPI 后端、Vite 前端、Chrome 调试及「全栈调试」复合配置

## 2026-08-03

- **生产部署**（`https://jb.jxfgg.com/qipai/`）：分支 `cursor/admin-all-expenses-export`（超管「全部报销」日期筛选 + 导出 Excel 等）；`scripts/deploy_prod.py --yes`
  - 本地备份：`backups/prod_20260803_185232/`（SQL + uploads 107 文件）
  - 线上备份：`/www/backup/qipai_20260803_185418/`（db dump + 前端 tar + 代码 tar + uploads）
  - 上传 `backend/app`、`backend/scripts` 与 `vite build --base=/qipai/` 前端包；迁移 `apply_expense_attachment_file`、`apply_expense_void` 无新增变更；Supervisor 重启 `qipai-api`，`/health` 正常

## 2026-07-28

- 报销单支持**超管作废**（方案 E）：新增状态 `VOIDED`；仅 `ADMIN` 可对「已完成」单据作废，须填写作废原因；记录作废人/时间；报表与导出自动排除已作废单据
- 迁移脚本：`sql/supabase/07-expense-voided.sql`、`python -m scripts.apply_expense_void`
- 新增 `scripts/sync_prod_to_dev.py` + `code/sync-prod-to-dev.ps1`：一键将生产 PostgreSQL 与 uploads 附件同步到 Supabase 开发库
- **生产 → Supabase 同步完成**：改用 plain SQL + psycopg2 写入（无需 pg_restore/Docker）；pooler 6543 自动切换 5432 会话模式执行 DDL；当前 Supabase 与线上一致（`expense_claim=64` 条 + 附件已下载至 `backend/uploads/`）
- **超管报销列表**：新增「全部报销」Tab；超管可查看全部单据并对「已完成」单据作废；「待我审批」仍仅显示指定您为审批人的待处理单
- 修复同步后缺少 `void_reason` 等字段：生产 dump 不含作废迁移，需额外执行 `python -m scripts.apply_expense_void`；同步脚本已自动在恢复后跑 `sql/supabase/*.sql`
- 修复「全部报销」为空：等待用户信息加载后再拉列表；三个列表独立加载，避免一个接口失败导致全部为空
- 优化报销报表 Tab 布局：筛选区与统计区分行、统计卡片栅格展示、分类明细独立卡片
- **生产部署**（2026-07-28）：新增 `scripts/deploy_prod.py`；本地备份 `backups/prod_20260728_223823/`；线上备份 `/www/backup/qipai_20260728_223909/`；部署作废功能 + 全部报销 Tab + 报表布局优化；执行 `apply_expense_void` 迁移
- 修复生产前端未重建：`deploy_prod.py` 改为每次部署强制 `npm run build`；补传含「全部报销」的前端包
- 报销报表「导出 Excel」对股东开放（前后端移除股东 403 限制）
- 超管「全部报销」：支持按提交日期 RangePicker 筛选；新增「导出 Excel」（`/api/v1/expenses/export/list`）
- 根目录 `README.md` 补充默认超管账号（admin / admin123）及重置说明

## 2026-07-23

- 报销附件由数据库 Base64 改为**磁盘静态文件**：上传落盘至 `backend/uploads/expenses/{claim_id}/{uuid}.ext`，DB 仅存 `file_path`；列表/详情 API 返回 `url` 不再带图片内容，解决列表接口 24MB/24 秒问题
- 本地开发：FastAPI 挂载 `/uploads` 静态目录，Vite 代理 `/uploads` → 8000
- 迁移：`sql/supabase/06-expense-attachment-file.sql` + `scripts.apply_expense_attachment_file` + `scripts.migrate_expense_attachments`（旧库 Base64 导出为文件）
- 生产 Nginx 需增加 `location /qipai/uploads/` alias 到 uploads 目录，并配置 `UPLOAD_DIR`、`UPLOAD_URL_PREFIX=/qipai/uploads`
- 根目录 `README.md` 补充**快速启动**（配置数据库、`start.ps1`、访问地址），详细说明仍见 `code/README.md`
- **生产部署**（`jb.jxfgg.com/qipai/`）：备份 DB 18MB + 站点 + 代码至 `/www/backup/qipai_20260723_115342/`；44 张报销附件 Base64 迁移至 `backend/uploads/`；前端 `vite build --base=/qipai/` 已上传；Nginx 增加 `location ^~ /qipai/uploads/`；Supervisor 重启 `qipai-api`

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
