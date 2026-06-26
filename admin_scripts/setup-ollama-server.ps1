# PC側: OllamaをLAN公開してラズパイからアクセスできるようにする
# 管理者権限で実行するとファイアウォール設定も行えます

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Ollama LAN公開セットアップ (PC側)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# OLLAMA_HOST を 0.0.0.0 に設定
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0", "User")
$env:OLLAMA_HOST = "0.0.0.0"
Write-Host '[OK] OLLAMA_HOST=0.0.0.0 を設定しました' -ForegroundColor Green

# モデルをメモリに保持（Cline 等で毎回再ロードされるのを防ぐ）
[System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "-1", "User")
$env:OLLAMA_KEEP_ALIVE = "-1"
Write-Host '[OK] OLLAMA_KEEP_ALIVE=-1 を設定しました' -ForegroundColor Green

# PCのIPアドレスを表示
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown"
} | Select-Object -First 1).IPAddress

Write-Host "[INFO] このPCのIPアドレス: $ip" -ForegroundColor Yellow
Write-Host '       ラズパイの config.py にこのIPを設定してください' -ForegroundColor Yellow

# ファイアウォール（管理者権限が必要）
try {
    $rule = Get-NetFirewallRule -DisplayName "Ollama API (LAN)" -ErrorAction SilentlyContinue
    if (-not $rule) {
        New-NetFirewallRule -DisplayName "Ollama API (LAN)" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow -Profile Any | Out-Null
        Write-Host '[OK] ファイアウォールルールを追加しました' -ForegroundColor Green
    } else {
        Write-Host '[OK] ファイアウォールルールは既に存在します' -ForegroundColor Green
    }
} catch {
    Write-Host '[WARN] ファイアウォール設定には管理者権限が必要です' -ForegroundColor Yellow
    Write-Host '       手動で TCP 11434 の受信を許可してください' -ForegroundColor Yellow
}

# Ollama再起動
Get-Process ollama, llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -WindowStyle Hidden
Start-Sleep -Seconds 5

# 確認
$listening = netstat -an | Select-String "0.0.0.0:11434"
if ($listening) {
    Write-Host '[OK] OllamaがLAN公開されています (0.0.0.0:11434)' -ForegroundColor Green
} else {
    Write-Host '[WARN] まだlocalhostのみの可能性があります。PCを再起動するかOllamaを手動で再起動してください' -ForegroundColor Yellow
}

try {
    $tags = Invoke-RestMethod -Uri "http://${ip}:11434/api/tags" -TimeoutSec 5
    Write-Host "[OK] LAN経由でAPIアクセス成功 ($($tags.models.Count) モデル)" -ForegroundColor Green
} catch {
    Write-Host "[WARN] LAN経由のAPIテスト失敗: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "  1. raspberry/ フォルダをラズパイにコピー"
Write-Host "  2. config.py の OLLAMA_HOST を $ip に設定"
Write-Host "  3. ラズパイで: bash setup.sh のあと llm-test"
