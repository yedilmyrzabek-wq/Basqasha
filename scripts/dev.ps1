# One-command dev start (Windows): backend API + Huey worker + frontend (if present).
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1     (Ctrl+C stops everything)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$logs = Join-Path $root "data\logs"
New-Item -ItemType Directory -Force $logs | Out-Null

# portable ffmpeg (docs/PLAN.md) if it is not on PATH yet
$ff = Join-Path $env:USERPROFILE "tools\ffmpeg\bin"
if ((Test-Path $ff) -and -not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { $env:PATH = "$ff;$env:PATH" }

function Get-EnvValue($name, $default) {
    $envFile = Join-Path $root ".env"
    if (Test-Path $envFile) {
        $line = Get-Content $envFile | Where-Object { $_ -match "^\s*$name\s*=" } | Select-Object -First 1
        if ($line) { return (($line -split "=", 2)[1] -split "#")[0].Trim() }
    }
    return $default
}
$apiHost = Get-EnvValue "BACKEND_HOST" "127.0.0.1"
$apiPort = Get-EnvValue "BACKEND_PORT" "8000"

Write-Host "Syncing backend dependencies (uv)..."
Push-Location $backend; uv sync --quiet; Pop-Location

$procs = @()
$procs += Start-Process uv -ArgumentList "run", "uvicorn", "app.main:app", "--host", $apiHost, "--port", $apiPort, "--reload", "--reload-dir", "app", "--reload-dir", "ai" `
    -WorkingDirectory $backend -NoNewWindow -PassThru
# worker restarts on code changes too (a step interrupted by a restart is marked failed -> «Повторить»)
$procs += Start-Process uv -ArgumentList "run", "watchfiles", "--filter", "python", "app.worker.main", "app", "ai" `
    -WorkingDirectory $backend -NoNewWindow -PassThru
$frontPort = [int](Get-EnvValue "FRONTEND_PORT" "5173")
$frontBusy = [bool](Get-NetTCPConnection -LocalPort $frontPort -State Listen -ErrorAction SilentlyContinue)
if ($frontBusy) {
    Write-Host "Port $frontPort is already in use - assuming the frontend dev server is running; not starting another"
} elseif (Test-Path (Join-Path $frontend "package.json")) {
    if (-not (Test-Path (Join-Path $frontend "node_modules"))) { Push-Location $frontend; npm install; Pop-Location }
    $procs += Start-Process npm.cmd -ArgumentList "run", "dev", "--", "--port", $frontPort, "--strictPort" `
        -WorkingDirectory $frontend -NoNewWindow -PassThru
} else {
    Write-Host "frontend/ not found - starting backend only"
}

Write-Host ""
Write-Host "API:      http://${apiHost}:${apiPort}/docs"
Write-Host "Frontend: http://localhost:$frontPort"
Write-Host "Ctrl+C to stop."
try {
    $running = $true
    while ($running) {
        Start-Sleep -Seconds 1
        foreach ($p in $procs) {
            if ($p.HasExited) { Write-Host "Process $($p.Id) exited - stopping the rest"; $running = $false }
        }
    }
} finally {
    foreach ($p in $procs) {
        if (-not $p.HasExited) { & taskkill /PID $p.Id /T /F 2>$null | Out-Null }
    }
    Write-Host "Stopped."
}
