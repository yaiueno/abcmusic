# Cline x Ollama: thinking ON/OFF switcher
# Usage:
#   .\switch-cline-mode.ps1           # menu
#   .\switch-cline-mode.ps1 -Mode fast    # thinking OFF -> port 11435
#   .\switch-cline-mode.ps1 -Mode think   # thinking ON  -> port 11436
#   .\switch-cline-mode.ps1 -StartProxies # start both proxies (background)

param(
    [ValidateSet("fast", "think", "menu", "start")]
    [string]$Mode = "menu"
)

$Root = $PSScriptRoot
$StateFile = Join-Path $Root ".cline-ollama-mode"
$FastPort = 11435
$ThinkPort = 11436
$Model = "qwen3.6-long"

function Test-Port($Port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $Port)
        $c.Close()
        return $true
    } catch { return $false }
}

function Start-Proxy($Port, $ThinkFlag) {
    if (Test-Port $Port) { return }
    $thinkVal = if ($ThinkFlag) { "true" } else { "false" }
    $env:OLLAMA_PROXY_PORT = "$Port"
    $env:OLLAMA_PROXY_THINK = $thinkVal
    Start-Process python -ArgumentList "`"$Root\ollama-cline-proxy.py`"" -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 300
        if (Test-Port $Port) { return }
    }
    Write-Host "[WARN] Proxy port $Port did not start" -ForegroundColor Yellow
}

function Set-ClineMode($Name, $Port, $ThinkLabel) {
    Start-Proxy $Port ($Name -eq "think")
    $url = "http://localhost:$Port"
    Set-Content -Path $StateFile -Value "$Name`n$url`n$ThinkLabel" -Encoding UTF8
    Set-Clipboard -Value $url
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " Cline mode: $ThinkLabel" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Base URL (copied): $url" -ForegroundColor Yellow
    Write-Host "Model: $Model"
    Write-Host "Provider: Ollama"
    Write-Host ""
    Write-Host "Cline settings -> paste Base URL -> Save" -ForegroundColor Cyan
}

function Show-Status {
    $fast = if (Test-Port $FastPort) { "running" } else { "stopped" }
    $think = if (Test-Port $ThinkPort) { "running" } else { "stopped" }
    Write-Host "Proxy status:" -ForegroundColor Cyan
    Write-Host "  :$FastPort fast (no think)  [$fast]"
    Write-Host "  :$ThinkPort think ON        [$think]"
    if (Test-Path $StateFile) {
        $lines = Get-Content $StateFile
        Write-Host "Last selected: $($lines[2]) -> $($lines[1])" -ForegroundColor Green
    }
    Write-Host ""
}

switch ($Mode) {
    "fast"  { Set-ClineMode "fast"  $FastPort "thinking OFF (fast)"; Show-Status; exit 0 }
    "think" { Set-ClineMode "think" $ThinkPort "thinking ON"; Show-Status; exit 0 }
    "start" {
        Start-Proxy $FastPort $false
        Start-Proxy $ThinkPort $true
        Write-Host "[OK] Both proxies started" -ForegroundColor Green
        Write-Host "  fast  -> http://localhost:$FastPort"
        Write-Host "  think -> http://localhost:$ThinkPort"
        Show-Status
        exit 0
    }
    default {
        Show-Status
        Write-Host "Select mode:" -ForegroundColor Cyan
        Write-Host "  1) fast  - thinking OFF (quick coding)"
        Write-Host "  2) think - thinking ON  (hard problems)"
        Write-Host "  3) start both proxies only"
        Write-Host "  q) quit"
        $c = Read-Host "Choice"
        switch ($c) {
            "1" { Set-ClineMode "fast"  $FastPort "thinking OFF (fast)" }
            "2" { Set-ClineMode "think" $ThinkPort "thinking ON" }
            "3" { Start-Proxy $FastPort $false; Start-Proxy $ThinkPort $true; Show-Status }
            default { exit 0 }
        }
        Show-Status
    }
}
