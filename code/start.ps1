# start.ps1 - backend :8000 + frontend :5180
# Usage: .\start.ps1  or double-click start.cmd
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$EnvFile = Join-Path $Backend ".env"
$EnvExample = Join-Path $Backend ".env.example"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Backend ".venv\Scripts\pip.exe"
$InitMarker = Join-Path $Backend ".dev-initialized"
$SetupDb = Join-Path $Root "setup-db.ps1"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Stop-BackendTree([System.Diagnostics.Process]$Process) {
    if (-not $Process -or $Process.HasExited) { return }
    try {
        & taskkill /T /F /PID $Process.Id 2>$null | Out-Null
    } catch {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Step "Check backend/.env"
if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Host "已从 .env.example 创建 backend/.env，请填写 Supabase DATABASE_URL。" -ForegroundColor Yellow
    } else {
        Write-Host "缺少 backend/.env，请配置 DATABASE_URL。" -ForegroundColor Red
    }
    exit 1
}

Write-Step "Check Python"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Install Python 3.10+ first." -ForegroundColor Red
    exit 1
}

$freshVenv = $false
if (-not (Test-Path $VenvPython)) {
    Write-Step "Create venv (.venv)"
    Push-Location $Backend
    python -m venv .venv
    Pop-Location
    $freshVenv = $true
}

Write-Step "Check backend dependencies"
$depsOk = $false
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
& $VenvPython -c "import uvicorn, fastapi, sqlalchemy, psycopg2" 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { $depsOk = $true }
$ErrorActionPreference = $prevEap

if (-not $depsOk) {
    Write-Step "pip install -r requirements.txt"
    & $VenvPip install -r (Join-Path $Backend "requirements.txt")
} else {
    Write-Host "Backend deps OK, skip pip install" -ForegroundColor DarkGray
}

if ($freshVenv -or -not (Test-Path $InitMarker)) {
    Write-Step "Check Supabase database connection"
    Push-Location $Backend
    & $VenvPython -m scripts.check_db
    $dbOk = $LASTEXITCODE -eq 0
    Pop-Location
    if (-not $dbOk) {
        Write-Host "无法连接 Supabase 数据库。" -ForegroundColor Red
        Write-Host "初始化步骤:" -ForegroundColor Yellow
        Write-Host '  1. 在 backend/.env 填写 DATABASE_URL，见 .env.example' -ForegroundColor Yellow
        Write-Host '  2. 运行 .\setup-db.ps1 初始化 schema 与 admin 账号' -ForegroundColor Yellow
        exit 1
    }

    Write-Step "Init admin (first run only)"
    Push-Location $Backend
    & $VenvPython -m scripts.init_admin
    $initOk = $LASTEXITCODE -eq 0
    Pop-Location
    if ($initOk) {
        New-Item -ItemType File -Path $InitMarker -Force | Out-Null
    } else {
        Write-Host "init_admin failed. Check DATABASE_URL and run .\setup-db.ps1 first." -ForegroundColor Yellow
        exit 1
    }
}

Write-Step "Check Node.js"
if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "node/npm not found. Install Node.js first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Step "npm install"
    Push-Location $Frontend
    npm install
    Pop-Location
} else {
    Write-Host "Frontend deps OK, skip npm install" -ForegroundColor DarkGray
}

Write-Step "Start backend http://127.0.0.1:8000"
$backendProc = Start-Process -FilePath $VenvPython `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000") `
    -WorkingDirectory $Backend `
    -PassThru -NoNewWindow

Start-Sleep -Seconds 2

Write-Step "Start frontend http://127.0.0.1:5180"
Write-Host "Login: admin / admin123" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both servers`n" -ForegroundColor Green

Push-Location $Frontend
try {
    npm run dev
} finally {
    Pop-Location
    Write-Step "Stop backend"
    Stop-BackendTree $backendProc
}
