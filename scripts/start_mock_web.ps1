param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:SOFT_REVIEW_PORT = "$Port"
$env:SOFT_REVIEW_AI_ENABLED = "false"
$env:SOFT_REVIEW_AI_PROVIDER = "mock"
$env:SOFT_REVIEW_AI_ENDPOINT = ""
$env:SOFT_REVIEW_AI_MODEL = ""
$env:SOFT_REVIEW_AI_API_KEY_ENV = ""

Write-Host "Starting mock web on http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host "Working directory: $repoRoot" -ForegroundColor DarkGray

py -m app.api.main
