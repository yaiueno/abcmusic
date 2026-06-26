# ABC Music Suite - 全サービス一括起動スクリプト
# 使い方: .\start.ps1
# 全サービスを並列で起動します。Ctrl+C で全停止。

$Root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ABC Music Suite - 全サービス起動" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- FastAPI バックエンド (ポート 8000) ---
Write-Host "[1/3] FastAPI バックエンドを起動中... (http://localhost:8000)" -ForegroundColor Yellow
$apiProc = Start-Process -PassThru -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "$env:OUTPUT_DIR='$Root\output'; cd '$Root\server'; python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"
) -WindowStyle Normal

Start-Sleep -Seconds 2

# --- MIDI サーバー (ポート 3001) ---
Write-Host "[2/3] MIDI サーバーを起動中... (http://localhost:3001)" -ForegroundColor Yellow
$midiInstalled = Test-Path "$Root\midi-server\node_modules"
if (-not $midiInstalled) {
    Write-Host "  → node_modules が見つかりません。npm install を実行します..." -ForegroundColor DarkYellow
    Start-Process -Wait -FilePath "npm" -ArgumentList "install" -WorkingDirectory "$Root\midi-server"
}
$midiProc = Start-Process -PassThru -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$Root\midi-server'; node server.js"
) -WindowStyle Normal

Start-Sleep -Seconds 1

# --- Vite フロントエンド (ポート 5173) ---
Write-Host "[3/3] Vite フロントエンドを起動中... (http://localhost:5173)" -ForegroundColor Yellow
$uiInstalled = Test-Path "$Root\web-ui\node_modules"
if (-not $uiInstalled) {
    Write-Host "  → node_modules が見つかりません。npm install を実行します..." -ForegroundColor DarkYellow
    Start-Process -Wait -FilePath "npm" -ArgumentList "install" -WorkingDirectory "$Root\web-ui"
}
$uiProc = Start-Process -PassThru -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$Root\web-ui'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   全サービス起動完了！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Web UI:       http://localhost:5173" -ForegroundColor White
Write-Host "  API:          http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "  MIDI Server:  http://localhost:3001" -ForegroundColor White
Write-Host ""
Write-Host "  ブラウザで http://localhost:5173 を開いてください。" -ForegroundColor Cyan
Write-Host "  各サービスのウィンドウを閉じると停止します。" -ForegroundColor DarkGray
Write-Host ""
