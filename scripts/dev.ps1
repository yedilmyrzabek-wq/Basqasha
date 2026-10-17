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

# Each service is restarted if it exits (e.g. the worker crashes on a half-saved file), so one
# failure never tears down the others. Ctrl+C stops everything.
$services = @(
    @{ Name = "api"; File = "uv"; Dir = $backend
       Args = @("run", "uvicorn", "app.main:app", "--host", $apiHost, "--port", $apiPort, "--reload", "--reload-dir", "app", "--reload-dir", "ai") },
    # worker restarts on code changes too (a step interrupted by a restart is marked failed -> «Повторить»)
    @{ Name = "worker"; File = "uv"; Dir = $backend; Args = @("run", "watchfiles", "--filter", "python", "app.worker.main", "app", "ai") }
)
$frontPort = [int](Get-EnvValue "FRONTEND_PORT" "5173")
$frontBusy = [bool](Get-NetTCPConnection -LocalPort $frontPort -State Listen -ErrorAction SilentlyContinue)
if ($frontBusy) {
    Write-Host "Port $frontPort is already in use - assuming the frontend dev server is running; not starting another"
} elseif (Test-Path (Join-Path $frontend "package.json")) {
    if (-not (Test-Path (Join-Path $frontend "node_modules"))) { Push-Location $frontend; npm install; Pop-Location }
    $services += @{ Name = "frontend"; File = "npm.cmd"; Dir = $frontend; Args = @("run", "dev", "--", "--port", $frontPort, "--strictPort") }
} else {
    Write-Host "frontend/ not found - starting backend only"
}
function Start-DevService($svc) {
    $svc.Proc = Start-Process $svc.File -ArgumentList $svc.Args -WorkingDirectory $svc.Dir -NoNewWindow -PassThru
}
foreach ($svc in $services) { Start-DevService $svc }

Write-Host ""
Write-Host "API:      http://${apiHost}:${apiPort}/docs"
Write-Host "Frontend: http://localhost:$frontPort"
Write-Host "Ctrl+C to stop."
try {
    while ($true) {
        Start-Sleep -Seconds 2
        foreach ($svc in $services) {
            if ($svc.Proc.HasExited) {
                Write-Host "[$($svc.Name)] exited (code $($svc.Proc.ExitCode)) - restarting in 3 s"
                Start-Sleep -Seconds 3
                Start-DevService $svc
            }
        }
    }
} finally {
    foreach ($svc in $services) {
        if ($svc.Proc -and -not $svc.Proc.HasExited) { & taskkill /PID $svc.Proc.Id /T /F 2>$null | Out-Null }
    }
    Write-Host "Stopped."
}
