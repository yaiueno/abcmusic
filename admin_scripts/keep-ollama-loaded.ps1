# Pin Ollama model in memory for Cline (same as: ollama run MODEL --keepalive -1)
# Usage: .\keep-ollama-loaded.ps1
#        .\keep-ollama-loaded.ps1 -Model "qwen3.6-long" -RestartOllama

param(
    [string]$Model = "qwen3.6-long",
    [switch]$Interactive,
    [switch]$RestartOllama
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Ollama keep-alive setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

[System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "-1", "User")
$env:OLLAMA_KEEP_ALIVE = "-1"
Write-Host "[OK] OLLAMA_KEEP_ALIVE=-1" -ForegroundColor Green

if ($RestartOllama) {
    Write-Host "[INFO] Restarting Ollama..." -ForegroundColor Yellow
    Get-Process ollama, llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    $ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    $env:OLLAMA_HOST = [System.Environment]::GetEnvironmentVariable("OLLAMA_HOST", "User")
    if (-not $env:OLLAMA_HOST) { $env:OLLAMA_HOST = "0.0.0.0" }
    Start-Process -FilePath $ollamaExe -WindowStyle Hidden
    Start-Sleep -Seconds 8
}

if ($Interactive) {
    Write-Host "[INFO] Opening ollama run in new window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "ollama run $Model --keepalive -1"
    Start-Sleep -Seconds 3
} else {
    Write-Host "[INFO] Loading $Model (may take 1-2 min)..." -ForegroundColor Yellow
    $body = @{ model = $Model; keep_alive = -1; prompt = "" } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 600 | Out-Null
        Write-Host "[OK] $Model pinned in memory" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Load failed: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Status:" -ForegroundColor Cyan
& ollama ps

Write-Host ""
Write-Host "UNTIL=Forever means ready for Cline" -ForegroundColor Green
Write-Host "Cline model name: $Model" -ForegroundColor Cyan
Write-Host "Unload: ollama stop $Model" -ForegroundColor Yellow
