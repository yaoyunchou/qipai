# 启动/停止本地 Docker PostgreSQL
# 用法: .\docker-db.ps1 up | down | status | logs
param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "status", "logs")]
    [string]$Action = "up"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Wait-PostgresReady {
    $max = 30
    for ($i = 1; $i -le $max; $i++) {
        docker compose -f (Join-Path $Root "docker-compose.yml") exec -T postgres pg_isready -U qipai -d qipai 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL 已就绪 (qipai@127.0.0.1:5432/qipai)" -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "PostgreSQL 启动超时，请执行 .\docker-db.ps1 logs 查看日志"
}

Push-Location $Root
try {
    switch ($Action) {
        "up" {
            Write-Host "==> 启动 Docker PostgreSQL ..." -ForegroundColor Cyan
            docker compose up -d
            Wait-PostgresReady
        }
        "down" {
            Write-Host "==> 停止 Docker PostgreSQL ..." -ForegroundColor Cyan
            docker compose down
        }
        "status" {
            docker compose ps
        }
        "logs" {
            docker compose logs -f postgres
        }
    }
} finally {
    Pop-Location
}
