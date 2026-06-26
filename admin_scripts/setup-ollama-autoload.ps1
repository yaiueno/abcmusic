# PC login autoload for qwen3.6-long (Cline)
# Usage: .\setup-ollama-autoload.ps1
# Remove: .\setup-ollama-autoload.ps1 -Remove

param(
    [string]$Model = "qwen3.6-long",
    [switch]$Remove
)

$TaskName = "Ollama-Preload-Cline"
$ScriptPath = Join-Path $PSScriptRoot "preload-ollama-hidden.ps1"

[System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "-1", "User")

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[OK] Autoload task removed" -ForegroundColor Green
    exit 0
}

$preloadScript = @"
`$Model = "$Model"
`$maxWait = 120
for (`$i = 0; `$i -lt `$maxWait; `$i += 5) {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
        break
    } catch {
        Start-Sleep -Seconds 5
    }
}
`$body = @{ model = `$Model; keep_alive = -1; prompt = "" } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body `$body -ContentType "application/json" -TimeoutSec 600 | Out-Null
} catch { }
"@

Set-Content -Path $ScriptPath -Value $preloadScript -Encoding UTF8

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Host "[OK] Registered logon task for $Model" -ForegroundColor Green
Write-Host "[OK] OLLAMA_KEEP_ALIVE=-1 set" -ForegroundColor Green
