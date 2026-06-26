# raspberry フォルダをラズパイにまるごとコピーする
# 使い方: .\copy-to-pi.ps1 -PiIP 192.168.0.179

param(
    [Parameter(Mandatory = $true)]
    [string]$PiIP,
    [string]$PiUser = "yoshito"
)

$src = Join-Path $PSScriptRoot "raspberry"
$required = @("config.py", "test_connection.py", "setup.sh", "abc_synthesizer.py", "play_abc.py")

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ラズパイへファイル転送 (yoshito@$PiIP)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

foreach ($f in $required) {
    $path = Join-Path $src $f
    if (Test-Path $path) {
        Write-Host "[OK] $f" -ForegroundColor Green
    } else {
        Write-Host "[NG] $f が見つかりません" -ForegroundColor Red
        exit 1
    }
}

$dest = $PiUser + "@" + $PiIP + ":~/"
Write-Host ""
Write-Host "転送先: $dest" -ForegroundColor Yellow
Write-Host "パスワードを聞かれたらラズパイのログインパスワードを入力してください"
Write-Host ""

scp -r $src $dest

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] 転送完了" -ForegroundColor Green
    Write-Host ""
    Write-Host "ラズパイで実行するコマンド:" -ForegroundColor Cyan
    Write-Host "  cd ~/raspberry"
    Write-Host "  bash setup.sh"
    Write-Host "  source ~/.bashrc"
    Write-Host "  llm-test"
} else {
    Write-Host "[NG] 転送失敗" -ForegroundColor Red
}
