param(
    [int]$Port = 18011,
    [string]$UpstreamBaseUrl = "https://api.minimaxi.com/v1",
    [string]$Model = "MiniMax-M2.7-highspeed",
    [string]$ApiKeyEnv = "MINIMAX_API_KEY"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$apiKeyValue = (Get-Item "Env:$ApiKeyEnv" -ErrorAction SilentlyContinue).Value
if (-not $apiKeyValue) {
    throw "Missing required environment variable: $ApiKeyEnv"
}

Write-Host "Starting MiniMax bridge on http://127.0.0.1:$Port/review" -ForegroundColor Cyan
Write-Host "Using upstream model: $Model" -ForegroundColor DarkGray
Write-Host "Working directory: $repoRoot" -ForegroundColor DarkGray

py -m app.tools.minimax_bridge `
    --port $Port `
    --upstream-base-url $UpstreamBaseUrl `
    --upstream-model $Model `
    --upstream-api-key-env $ApiKeyEnv `
    --request-log-path data/runtime/logs/minimax_bridge_live.jsonl
