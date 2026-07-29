# 一键：生产数据 -> Supabase（backend/.env 里的 DATABASE_URL）
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$RepoRoot = Split-Path $Root -Parent
$Python = Join-Path $Root "backend\.venv\Scripts\python.exe"

Write-Host "==> 同步生产数据到 Supabase" -ForegroundColor Cyan
& $Python -m pip install paramiko python-dotenv -q 2>$null
& $Python "$RepoRoot\scripts\sync_prod_to_dev.py" @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n完成。" -ForegroundColor Green
