# Cline MCP: local web search (no Ollama cloud / no API key)
#
# Usage:
#   .\setup-cline-mcp-search.ps1          # DuckDuckGo MCP (default, simplest)
#   .\setup-cline-mcp-search.ps1 -SearXNG # SearXNG + MCP (needs Docker Desktop running)

param(
    [switch]$SearXNG
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$ClineMcp = Join-Path $env:APPDATA "Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Command node)) {
    Write-Host "Node.js is required for MCP. Install from https://nodejs.org/" -ForegroundColor Red
    exit 1
}

if ($SearXNG) {
    if (-not (Test-Command docker)) {
        Write-Host "Docker is required for SearXNG." -ForegroundColor Red
        exit 1
    }

    $SearxDir = Join-Path $Root "searxng"
    $SettingsYml = Join-Path $SearxDir "settings.yml"
    New-Item -ItemType Directory -Force -Path $SearxDir | Out-Null

    if (-not (Test-Path $SettingsYml)) {
        @"
use_default_settings: true
search:
  formats:
    - html
    - json
server:
  secret_key: "change-me-local-only"
"@ | Set-Content -Path $SettingsYml -Encoding UTF8
    }

    docker rm -f searxng 2>$null | Out-Null
    docker run -d --name searxng -p 8888:8080 `
        -v "${SearxDir}:/etc/searxng" `
        -e "SEARXNG_BASE_URL=http://localhost:8888/" `
        searxng/searxng | Out-Null

    Start-Sleep -Seconds 3
    Write-Host "SearXNG: http://localhost:8888" -ForegroundColor Green

    $config = @{
        mcpServers = @{
            searxng = @{
                command = "npx"
                args    = @("-y", "mcp-searxng")
                env     = @{ SEARXNG_URL = "http://localhost:8888" }
                disabled = $false
            }
        }
    }
} else {
    Write-Host "Mode: DuckDuckGo MCP (no Docker, no API key)" -ForegroundColor Cyan

    $config = @{
        mcpServers = @{
            duckduckgo = @{
                command  = "npx"
                args     = @("-y", "duckduckgo-mcp-server")
                disabled = $false
            }
        }
    }
}

$dir = Split-Path $ClineMcp -Parent
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$config | ConvertTo-Json -Depth 5 | Set-Content -Path $ClineMcp -Encoding UTF8

Write-Host ""
Write-Host "Wrote: $ClineMcp" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Reload VS Code / Cline window"
Write-Host "  2. Cline -> MCP Servers -> enable duckduckgo (or searxng)"
Write-Host "  3. Ollama: qwen3.6-long + cline-fast.bat (think OFF recommended for search)"
Write-Host "  4. Ask: 'DuckDuckGo MCPで今日のニュースを調べて'"
