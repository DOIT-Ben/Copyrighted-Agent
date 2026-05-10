param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\start_uv_web.ps1" -Port $Port -Mock
