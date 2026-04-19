param(
    [int]$Port = 8000,
    [string]$Endpoint = "http://127.0.0.1:18011/review",
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
$env:SOFT_REVIEW_PORT = "$Port"
$env:SOFT_REVIEW_AI_ENABLED = "true"
$env:SOFT_REVIEW_AI_PROVIDER = "external_http"
$env:SOFT_REVIEW_AI_ENDPOINT = $Endpoint
$env:SOFT_REVIEW_AI_MODEL = $Model
$env:SOFT_REVIEW_AI_API_KEY_ENV = $ApiKeyEnv
$env:SOFT_REVIEW_AI_REQUIRE_DESENSITIZED = "true"

Write-Host "Starting real web on http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host "Bridge endpoint: $Endpoint" -ForegroundColor DarkGray
Write-Host "Model: $Model" -ForegroundColor DarkGray
Write-Host "Working directory: $repoRoot" -ForegroundColor DarkGray

py -m app.api.main
