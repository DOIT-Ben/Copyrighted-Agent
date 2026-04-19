param(
    [string]$ConfigPath = "config\local.json",
    [string]$ModeAPath = "",
    [string]$ModeBPath = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

function Resolve-DefaultModeAPath {
    $candidate = Get-ChildItem -Path "input" -Recurse -File -Filter "2501_*.zip" -ErrorAction SilentlyContinue |
        Sort-Object FullName |
        Select-Object -First 1
    if ($candidate) {
        return $candidate.FullName
    }
    throw "Could not auto-resolve a Mode A sample ZIP under input\\."
}

function Resolve-DefaultModeBPath {
    $candidate = Get-ChildItem -Path "input" -Directory -ErrorAction SilentlyContinue |
        Where-Object {
            (
                Get-ChildItem -Path $_.FullName -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Extension -in ".doc", ".docx", ".pdf", ".txt" } |
                Measure-Object
            ).Count -ge 5
        } |
        Sort-Object FullName |
        Select-Object -First 1
    if ($candidate) {
        return $candidate.FullName
    }
    throw "Could not auto-resolve a Mode B sample directory under input\\."
}

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if (-not $ModeAPath) {
    $ModeAPath = Resolve-DefaultModeAPath
}
if (-not $ModeBPath) {
    $ModeBPath = Resolve-DefaultModeBPath
}

Write-Host "Running real-provider validation..." -ForegroundColor Cyan
Write-Host "Config: $ConfigPath" -ForegroundColor DarkGray
Write-Host "Mode A: $ModeAPath" -ForegroundColor DarkGray
Write-Host "Mode B: $ModeBPath" -ForegroundColor DarkGray

py -m app.tools.release_validation `
    --config $ConfigPath `
    --mode-a-path $ModeAPath `
    --mode-b-path $ModeBPath `
    --json
