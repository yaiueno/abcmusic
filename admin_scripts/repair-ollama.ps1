# Ollama repair: rebuild qwen3.6-long + pin in memory
# Usage: .\repair-ollama.ps1

$Root = $PSScriptRoot

Write-Host "[1/4] Rebuilding qwen3.6-long (num_ctx=32768)..." -ForegroundColor Cyan
Push-Location $Root
ollama create qwen3.6-long -f Modelfile.qwen3.6-long
Pop-Location

Write-Host "[2/4] Removing broken nothink variant from default use..." -ForegroundColor Cyan
Write-Host "      Use qwen3.6-long + think=false instead of qwen3.6-long-nothink"

Write-Host "[3/4] Pinning qwen3.6-long..." -ForegroundColor Cyan
& "$Root\keep-ollama-loaded.ps1" -Model "qwen3.6-long"

Write-Host "[4/4] Quick test..." -ForegroundColor Cyan
$body = @{
    model = "qwen3.6-long"
    think = $false
    messages = @(@{ role = "user"; content = "say hi" })
    stream = $false
} | ConvertTo-Json -Depth 5
$r = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 120
Write-Host "Response: $($r.message.content)" -ForegroundColor Green
ollama ps

Write-Host ""
Write-Host "GUI/Cline tips:" -ForegroundColor Yellow
Write-Host "  Model: qwen3.6-long (NOT qwen3.6-long-nothink)"
Write-Host "  GUI: /set nothink  or thinking OFF"
Write-Host "  Cline fast: cline-fast.bat (port 11435)"
