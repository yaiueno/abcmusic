# qwen3.6-long を Modelfile 設定で再ビルドしてメモリ固定
# Usage: .\rebuild-qwen3.6-long.ps1

$Root = $PSScriptRoot
$Modelfile = Join-Path $Root "Modelfile.qwen3.6-long"

Write-Host "[1/3] Rebuilding qwen3.6-long (num_ctx from Modelfile)..." -ForegroundColor Cyan
Push-Location $Root
ollama create qwen3.6-long -f $Modelfile
Pop-Location

Write-Host "[2/3] Pinning model in memory..." -ForegroundColor Cyan
& (Join-Path $Root "keep-ollama-loaded.ps1") -Model "qwen3.6-long"

Write-Host "[3/3] Verify CONTEXT in ollama ps (target: 131072)" -ForegroundColor Cyan
ollama ps
