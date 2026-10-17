# Desktop launcher: starts the app (scripts\dev.ps1) and opens the browser when it is ready.
# If the app is already running, it only opens the browser. Closing this window stops the app.
$root = Split-Path -Parent $PSScriptRoot
$url = "http://localhost:5173"
$Host.UI.RawUI.WindowTitle = "Basqasha"

function Test-Up {
    try { (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch { $false }
}

if (Test-Up) {
    Start-Process $url
    exit 0
}

# open the browser as soon as the frontend answers (up to 3 minutes)
Start-Job -ArgumentList $url -ScriptBlock {
    param($u)
    for ($i = 0; $i -lt 180; $i++) {
        try {
            if ((Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { Start-Process $u; return }
        } catch {}
        Start-Sleep -Seconds 1
    }
} | Out-Null

Write-Host "Basqasha запускается... браузер откроется сам. Не закрывайте это окно, пока работаете." -ForegroundColor Green
& (Join-Path $PSScriptRoot "dev.ps1")
