# ローカルLLM チャット起動スクリプト (Ollama)
# 使い方: .\chat.ps1
#         .\chat.ps1 -Model qwen2.5-coder:7b

param(
    [string]$Model = "qwen2.5:7b"
)

$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

if (-not (Test-Path $ollama)) {
    Write-Host "Ollama が見つかりません。インストールしてください: https://ollama.com" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ローカルLLM チャット ($Model)" -ForegroundColor Cyan
Write-Host " 終了: /bye または Ctrl+C" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& $ollama run $Model
