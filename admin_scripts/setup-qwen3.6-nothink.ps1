# qwen3.6-long の no-think 版（131K context）
# 注意: Ollama 0.30 では Modelfile だけでは thinking 完全OFF不可
# Cline 向けは start-ollama-nothink-proxy.bat を使う（think=false 注入）
# チャット単体: ollama run qwen3.6-long-nothink --think=false

param(
    [switch]$Rebuild
)

$Root = $PSScriptRoot
$Modelfile = Join-Path $Root "Modelfile.qwen3.6-long-nothink"

if ($Rebuild -or -not (ollama list 2>$null | Select-String "qwen3.6-long-nothink")) {
    Write-Host "[1/2] Building qwen3.6-long-nothink..." -ForegroundColor Cyan
    Push-Location $Root
    ollama create qwen3.6-long-nothink -f $Modelfile
    Pop-Location
}

Write-Host "[2/2] Pinning model..." -ForegroundColor Cyan
& (Join-Path $Root "keep-ollama-loaded.ps1") -Model "qwen3.6-long-nothink"

Write-Host "Cline (recommended):" -ForegroundColor Green
Write-Host "  cline-fast.bat   -> thinking OFF (port 11435)"
Write-Host "  cline-think.bat  -> thinking ON  (port 11436)"
Write-Host "  switch-cline-mode.ps1  -> menu"
