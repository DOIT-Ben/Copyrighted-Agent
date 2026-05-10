param(
    [int]$Port = 8000,
    [string]$Endpoint = "http://127.0.0.1:18011/review",
    [string]$Model = "MiniMax-M2.7-highspeed",
    [string]$ApiKeyEnv = "MINIMAX_API_KEY"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\start_uv_web.ps1" `
    -Port $Port `
    -Endpoint $Endpoint `
    -Model $Model `
    -ApiKeyEnv $ApiKeyEnv
