$Model = "qwen3.6-long"
$maxWait = 120
for ($i = 0; $i -lt $maxWait; $i += 5) {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
        break
    } catch {
        Start-Sleep -Seconds 5
    }
}
$body = @{ model = $Model; keep_alive = -1; prompt = "" } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 600 | Out-Null
} catch { }
