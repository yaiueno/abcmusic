# ABC Music Suite - LAN ホスティング起動スクリプト
# ラズパイ等からブラウザでアクセスできるようにする
# 使い方: .\host.ps1

$Root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ABC Music Suite - LAN ホスティング" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: フロントエンドをビルド ---
Write-Host "[1/4] フロントエンドをビルド中..." -ForegroundColor Yellow

$uiInstalled = Test-Path "$Root\web-ui\node_modules"
if (-not $uiInstalled) {
    Write-Host "  → npm install 実行中..." -ForegroundColor DarkYellow
    Start-Process -Wait -FilePath "cmd" -ArgumentList "/c npm install" -WorkingDirectory "$Root\web-ui" -NoNewWindow
}

# VITE_API_BASE を空にしてビルド（同一Originを使う本番ビルド）
$buildResult = Start-Process -Wait -PassThru -FilePath "cmd" -ArgumentList "/c npm run build" -WorkingDirectory "$Root\web-ui" -NoNewWindow
if ($buildResult.ExitCode -ne 0) {
    Write-Host "  ❌ ビルド失敗！ npm run build のエラーを確認してください。" -ForegroundColor Red
    exit 1
}
Write-Host "  ✅ ビルド完了 → web-ui/dist/" -ForegroundColor Green

# --- Step 2: Windowsファイアウォール設定 ---
Write-Host "[2/4] Windowsファイアウォールでポート 8000 を開放中..." -ForegroundColor Yellow
$ruleName = "ABC-Music-Suite-API"
$existing = netsh advfirewall firewall show rule name=$ruleName 2>&1
if ($existing -notmatch "Rule Name") {
    netsh advfirewall firewall add rule `
        name=$ruleName `
        dir=in `
        action=allow `
        protocol=TCP `
        localport=8000 `
        description="ABC Music Suite FastAPI (LAN hosting)" | Out-Null
    Write-Host "  ✅ ファイアウォールルール追加完了" -ForegroundColor Green
} else {
    Write-Host "  ✅ ファイアウォールルールは既に存在します" -ForegroundColor Green
}

# --- Step 3: MIDI サーバー (内部のみ、ポート3001) ---
Write-Host "[3/4] MIDI サーバーを起動中... (内部: localhost:3001)" -ForegroundColor Yellow
$midiInstalled = Test-Path "$Root\midi-server\node_modules"
if (-not $midiInstalled) {
    Start-Process -Wait -FilePath "cmd" -ArgumentList "/c npm install" -WorkingDirectory "$Root\midi-server" -NoNewWindow
}
$midiProc = Start-Process -PassThru -FilePath "cmd" -ArgumentList "/c node server.js" -WorkingDirectory "$Root\midi-server" -WindowStyle Minimized

Start-Sleep -Seconds 1

# --- Step 4: FastAPI を 0.0.0.0 (LAN公開) で起動 ---
Write-Host "[4/4] FastAPI を LAN 公開モードで起動中... (0.0.0.0:8000)" -ForegroundColor Yellow

# PCのIPアドレスを表示
$lanIP = (Get-NetIPAddress -AddressFamily IPv4 | 
    Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.PrefixOrigin -eq 'Dhcp' } | 
    Select-Object -First 1).IPAddress
if (-not $lanIP) {
    $lanIP = (Get-NetIPAddress -AddressFamily IPv4 | 
        Where-Object { $_.InterfaceAlias -notmatch 'Loopback' } | 
        Select-Object -First 1).IPAddress
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   起動完了！ラズパイからアクセスできます" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  🍓 ラズパイのブラウザで開く:" -ForegroundColor White
Write-Host "     http://$lanIP`:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "  💻 このPCから開く:" -ForegroundColor White
Write-Host "     http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "  📖 API ドキュメント:" -ForegroundColor White
Write-Host "     http://$lanIP`:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ⚠️  Ctrl+C でサーバーを停止します" -ForegroundColor DarkGray
Write-Host ""

# FastAPI をこのウィンドウで実行（Ctrl+C で停止）
Set-Location "$Root\server"
$env:API_HOST = "0.0.0.0"
$env:API_PORT = "8000"
$env:OUTPUT_DIR = "$Root\output"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
