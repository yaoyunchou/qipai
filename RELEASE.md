# 发布流程规范

> 目的：杜绝「任意分支直接部署」，保证线上版本 = 已合并进 `main` 且已推送的代码。

---

## 一、铁律

| 规则 | 说明 |
|---|---|
| **只从 `main` 部署** | 任何开发分支、临时分支一律禁止部署 |
| **必须已合并** | 部署前代码必须已合并进 `main` |
| **必须已推送** | 本地 `main` 与 `origin/main` 必须完全一致 |
| **必须无差异** | 工作区干净，无未提交改动、无未跟踪文件 |
| **先迁移后上线** | 数据库迁移成功后才能上传新代码 |

`scripts/deploy_prod.py` 已内置上述校验，任何一条不满足会**直接中止并打印修复指引**。

---

## 二、标准流程（5 步）

### 1. 开发分支完成

```bash
git checkout -b feat/你的功能
# ... 开发、测试 ...
git add <具体文件>          # 不要 git add -A，避免误提交
git commit -m "feat: 具体描述"
```

**提交前自查清单：**

- [ ] 没有提交 `code/mp-weixin/`（微信小程序，与网页版无关）
- [ ] 没有提交 `.vscode/`、`__pycache__`、`.env`
- [ ] 没有提交临时脚本（如 `_probe_*.py`）
- [ ] 提交信息是具体功能描述，不是 `feat:优化`

### 2. 合并到 main

```bash
git checkout main
git pull origin main
git merge --no-ff feat/你的功能 -m "merge: 你的功能"
```

`--no-ff` 保留合并记录，便于日后回溯与回滚。

### 3. 推送

```bash
git push origin main
```

### 4. 部署前 dry-run 校验

```bash
code\backend\.venv\Scripts\python.exe scripts\deploy_prod.py --check
```

只做校验不部署，确认输出「前置校验通过」。

### 5. 部署

```bash
code\backend\.venv\Scripts\python.exe scripts\deploy_prod.py --yes
```

部署脚本会依次执行：

1. **前置校验**（分支 / 工作区 / 推送状态 / 与 origin/main 一致性）
2. **本地备份**：从生产拉取 SQL + uploads
3. **线上备份**：DB dump + 前端 tar + 代码 tar + 附件 tar → `/www/backup/qipai_<时间戳>/`
4. **数据库迁移**（幂等，先迁移后上传代码）
5. **上传代码 + 前端产物**（`--base=/qipai/`）
6. **重启 `qipai-api`** + 健康检查

---

## 三、禁止事项

| ❌ 禁止 | ✅ 正确做法 |
|---|---|
| 在 `feat/*`、`cursor/*` 分支直接部署 | 先合并到 `main` 再部署 |
| 工作区有未提交改动就部署 | 先提交或 stash |
| 本地 main 未 push 就部署 | 先 `git push origin main` |
| `git add -A` / `git add .` | 逐个指定文件或目录 |
| 迁移失败后继续上传代码 | 脚本已强制中止，修复迁移后重跑 |
| 用 `--yes` 跳过人工确认做实验 | 用 `--check` 只校验 |

---

## 四、回滚

### 代码回滚

线上代码每次部署前已打包至 `/www/backup/qipai_<时间戳>/code/`：

```bash
ssh root@<服务器>
cd /www/backup/qipai_<时间戳>/code
tar -xzf qipai_code_<时间戳>.tar.gz -C /www/server
supervisorctl restart qipai-api
```

### 数据库回滚

```bash
# 恢复前务必确认已在维护窗口
PGPASSWORD=<密码> pg_restore -h 127.0.0.1 -U qipai -d qipai --clean \
  /www/backup/qipai_<时间戳>/db/qipai_<时间戳>.dump
```

### 前端回滚

```bash
cd /www/backup/qipai_<时间戳>/site
tar -xzf qipai_frontend_<时间戳>.tar.gz -C /www/wwwroot/jb.jxfgg.com
```

> 目录名 `jb.jxfgg.com` 是历史遗留的实际路径，与对外域名无关，**不要改**。

---

## 五、生产域名

| 域名 | 角色 | 备注 |
|---|---|---|
| `jd.jxfg.top` | **主域名** | 部署脚本的完成提示、文档均以此为准 |
| `www.jxfg.top` | 备用 | 同一目录 |
| `jb.jxfgg.com` | 旧域名 | 同一目录，证书 2026-12-07 到期，后续可考虑下线 |

三者 Nginx `root` 与 `/qipai/` 的 `alias` 均指向 `/www/wwwroot/jb.jxfgg.com/qipai/`，
所以**一次部署对所有域名同时生效**。部署脚本会用 `Host` 头逐个验证三个域名的可访问性。

---

## 六、数据库迁移约定

- 所有迁移脚本必须**幂等**（`IF NOT EXISTS` / `EXCEPTION WHEN duplicate_object`）
- 新增迁移时，同步更新 `scripts/deploy_prod.py` 里的 `MIGRATIONS` 与 `MIGRATION_SCRIPTS`
- 枚举新增值（如 `ALTER TYPE ... ADD VALUE`）需在自动提交模式执行
- `CREATE TYPE ... ENUM` 若已存在会被 `EXCEPTION` 吞掉，**不会自动补新值**，必须另写 `ALTER TYPE ... ADD VALUE`

---

## 七、分支命名

| 前缀 | 用途 |
|---|---|
| `feat/` | 新功能 |
| `fix/` | 缺陷修复 |
| `refactor/` | 重构（不改行为） |
| `docs/` | 文档 |
| `cursor/` | AI 辅助开发的临时分支（**禁止直接部署**） |
