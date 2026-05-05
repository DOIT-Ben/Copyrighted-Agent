param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

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

$uvCommand = Resolve-UvCommand
Write-Host "Using uv: $($uvCommand -join ' ')" -ForegroundColor Cyan

$uvExe = $uvCommand[0]
$uvArgs = @()
if ($uvCommand.Count -gt 1) {
    $uvArgs = $uvCommand[1..($uvCommand.Count - 1)]
}

if ($Dev) {
    & $uvExe @uvArgs sync --dev
} else {
    & $uvExe @uvArgs sync
}
