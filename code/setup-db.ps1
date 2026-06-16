# setup-db.ps1 - 在 Supabase 上初始化数据库 schema
# 前置：backend/.env 已配置 DATABASE_URL
# 用法: .\setup-db.ps1
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$EnvFile = Join-Path $Backend ".env"
$EnvExample = Join-Path $Backend ".env.example"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Backend ".venv\Scripts\pip.exe"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

Write-Step "Check backend/.env"
if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Host "已从 .env.example 复制 backend/.env，请填写 DATABASE_URL 后重新运行。" -ForegroundColor Yellow
    } else {
        Write-Host "缺少 backend/.env，请创建并设置 Supabase DATABASE_URL。" -ForegroundColor Red
    }
    exit 1
}

$content = Get-Content $EnvFile -Raw
if ($content -notmatch 'DATABASE_URL\s*=\s*\S+' -or $content -match 'DATABASE_URL\s*=\s*$') {
    Write-Host "backend/.env 中 DATABASE_URL 未配置。" -ForegroundColor Red
    Write-Host "在 Supabase Dashboard → Project Settings → Database 复制连接串。" -ForegroundColor Yellow
    Write-Host "格式: postgresql+psycopg2://postgres.[ref]:[password]@...pooler.supabase.com:6543/postgres" -ForegroundColor Yellow
    exit 1
}

Write-Step "Check Python venv"
if (-not (Test-Path $VenvPython)) {
    Push-Location $Backend
    python -m venv .venv
    Pop-Location
}

Write-Step "Install backend dependencies"
& $VenvPip install -r (Join-Path $Backend "requirements.txt") -q

Write-Step "Apply Supabase schema (sql/supabase/01-init-schema.sql)"
Push-Location $Backend
& $VenvPython -m scripts.apply_schema
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }

Write-Step "Init admin account"
& $VenvPython -m scripts.init_admin
$initOk = $LASTEXITCODE -eq 0
Pop-Location

if (-not $initOk) { exit 1 }

Write-Host ""
Write-Host "Supabase 数据库就绪。运行 .\start.ps1 启动应用。" -ForegroundColor Green
Write-Host "默认登录: admin / admin123" -ForegroundColor Green
