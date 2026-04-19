param(
    [string]$ConfigPath = "config\local.json"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

function Show-PortStatus {
    param([int]$Port)

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $procId = $conn[0].OwningProcess
        Write-Host ("Port {0}: LISTEN (PID {1})" -f $Port, $procId) -ForegroundColor Green
    }
    else {
        Write-Host ("Port {0}: FREE" -f $Port) -ForegroundColor Yellow
    }
}

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

Write-Host "Repository: $repoRoot" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $ConfigPath) {
    $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    Write-Host "Config file:" -ForegroundColor Cyan
    Write-Host ("  host={0}" -f $config.host)
    Write-Host ("  port={0}" -f $config.port)
    Write-Host ("  ai_enabled={0}" -f $config.ai_enabled)
    Write-Host ("  ai_provider={0}" -f $config.ai_provider)
    Write-Host ("  ai_endpoint={0}" -f $config.ai_endpoint)
    Write-Host ("  ai_model={0}" -f $config.ai_model)
    Write-Host ("  ai_api_key_env={0}" -f $config.ai_api_key_env)
    Write-Host ""
}
else {
    Write-Host "Config file missing: $ConfigPath" -ForegroundColor Yellow
    Write-Host ""
}

$bridgeKey = ""
if (Test-Path $ConfigPath) {
    $bridgeKey = (Get-Content $ConfigPath -Raw | ConvertFrom-Json).ai_api_key_env
}

if ($bridgeKey) {
    $present = [bool](Get-Item "Env:$bridgeKey" -ErrorAction SilentlyContinue)
    Write-Host ("API key env ({0}) present: {1}" -f $bridgeKey, $present) -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Port status:" -ForegroundColor Cyan
Show-PortStatus -Port 8000
Show-PortStatus -Port 18011
Show-PortStatus -Port 18080

$latestValidation = "docs\dev\real-provider-validation-latest.md"
if (Test-Path $latestValidation) {
    Write-Host ""
    Write-Host "Latest validation artifact: $latestValidation" -ForegroundColor Cyan
}
