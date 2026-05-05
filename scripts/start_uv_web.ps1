param(
    [int]$Port = 8000,
    [switch]$Mock,
    [string]$Endpoint = "http://127.0.0.1:18011/review",
    [string]$Model = "MiniMax-M2.7-highspeed",
    [string]$ApiKeyEnv = "MINIMAX_API_KEY"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\ensure_uv.ps1" -Dev

function Resolve-UvCommand {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        return @("uv")
    }

    $pythonCandidates = @(
        ".venv\Scripts\python.exe",
        "C:\Users\DOIT\miniconda3\python.exe",
        "py",
        "python"
    )

    foreach ($candidate in $pythonCandidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if (-not $command) {
            continue
        }
        try {
            & $candidate -m uv --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return @($candidate, "-m", "uv")
            }
        } catch {
            continue
        }
    }

    throw "uv is not available. Install it first: py -m pip install uv"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:SOFT_REVIEW_PORT = "$Port"

if ($Mock) {
    $env:SOFT_REVIEW_AI_ENABLED = "false"
    $env:SOFT_REVIEW_AI_PROVIDER = "mock"
    $env:SOFT_REVIEW_AI_ENDPOINT = ""
    $env:SOFT_REVIEW_AI_MODEL = ""
    $env:SOFT_REVIEW_AI_API_KEY_ENV = ""
    Write-Host "Starting Copyrighted Agent in mock mode: http://127.0.0.1:$Port" -ForegroundColor Cyan
} else {
    $env:SOFT_REVIEW_AI_ENABLED = "true"
    $env:SOFT_REVIEW_AI_PROVIDER = "external_http"
    $env:SOFT_REVIEW_AI_ENDPOINT = $Endpoint
    $env:SOFT_REVIEW_AI_MODEL = $Model
    $env:SOFT_REVIEW_AI_API_KEY_ENV = $ApiKeyEnv
    $env:SOFT_REVIEW_AI_REQUIRE_DESENSITIZED = "true"
    Write-Host "Starting Copyrighted Agent in real-provider mode: http://127.0.0.1:$Port" -ForegroundColor Cyan
    Write-Host "Bridge endpoint: $Endpoint" -ForegroundColor DarkGray
    Write-Host "Model: $Model" -ForegroundColor DarkGray
    Write-Host "API key env: $ApiKeyEnv" -ForegroundColor DarkGray
}

$uvCommand = Resolve-UvCommand
$uvExe = $uvCommand[0]
$uvArgs = @()
if ($uvCommand.Count -gt 1) {
    $uvArgs = $uvCommand[1..($uvCommand.Count - 1)]
}

& $uvExe @uvArgs run python -m app.api.main
