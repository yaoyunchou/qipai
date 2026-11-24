# 本地 Docker 数据库一键初始化：启动容器 → 建表 → 创建 admin
# 用法: .\setup-local-db.ps1
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$EnvFile = Join-Path $Backend ".env"
$EnvLocal = Join-Path $Backend ".env.local.docker"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Backend ".venv\Scripts\pip.exe"

Write-Host ""
Write-Host "==> 启动 Docker PostgreSQL" -ForegroundColor Cyan
& (Join-Path $Root "docker-db.ps1") up

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvLocal) {
        Copy-Item $EnvLocal $EnvFile
        Write-Host "已从 .env.local.docker 复制 backend/.env" -ForegroundColor Yellow
    } else {
        Write-Host "缺少 backend/.env，请先配置本地 DATABASE_URL。" -ForegroundColor Red
        exit 1
    }
}

$content = Get-Content $EnvFile -Raw
if ($content -notmatch 'DATABASE_URL\s*=\s*\S+' -or $content -match 'DATABASE_URL\s*=\s*$') {
    Write-Host "backend/.env 中 DATABASE_URL 未配置。" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VenvPython)) {
    Push-Location $Backend
    python -m venv .venv
    Pop-Location
}

Write-Host ""
Write-Host "==> 安装后端依赖" -ForegroundColor Cyan
& $VenvPip install -r (Join-Path $Backend "requirements.txt") -q

Write-Host ""
Write-Host "==> 应用 schema" -ForegroundColor Cyan
Push-Location $Backend
& $VenvPython -m scripts.apply_schema
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }

Write-Host ""
Write-Host "==> 应用报销模块迁移" -ForegroundColor Cyan
& $VenvPython -m scripts.apply_expense_schema
& $VenvPython -m scripts.apply_expense_category
& $VenvPython -m scripts.apply_expense_category_living
& $VenvPython -m scripts.apply_expense_attachment_file
& $VenvPython -m scripts.apply_expense_void
& $VenvPython -m scripts.apply_play_companion
& $VenvPython -m scripts.apply_play_companion_signed_amount
& $VenvPython -m scripts.apply_loan_record
& $VenvPython -m scripts.apply_companion_staff

Write-Host ""
Write-Host "==> 创建 admin 账号" -ForegroundColor Cyan
& $VenvPython -m scripts.init_admin
$initOk = $LASTEXITCODE -eq 0
Pop-Location

if (-not $initOk) { exit 1 }

Write-Host ""
Write-Host "本地数据库就绪。运行 .\start.ps1 启动应用。" -ForegroundColor Green
Write-Host "默认登录: admin / admin123" -ForegroundColor Green
Write-Host "DATABASE_URL=postgresql+psycopg2://qipai:qipai_local_dev@127.0.0.1:5432/qipai" -ForegroundColor DarkGray
