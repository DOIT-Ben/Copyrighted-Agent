param(
    [int]$BridgePort = 18011,
    [int]$WebPort = 18080,
    [string]$UpstreamBaseUrl = "https://api.minimaxi.com/v1",
    [string]$Model = "MiniMax-M2.7-highspeed",
    [string]$ApiKeyEnv = "MINIMAX_API_KEY",
    [string]$ApiKey = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

function Stop-ListeningProcess {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return
    }

    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host ("Stopped PID {0} on port {1}" -f $processId, $Port) -ForegroundColor Yellow
        }
        catch {
            Write-Host ("Failed to stop PID {0} on port {1}: {2}" -f $processId, $Port, $_.Exception.Message) -ForegroundColor Red
        }
    }
}

function Wait-PortReady {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listener) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    while ((Get-Date) -lt $deadline)

    return $false
}

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

if ($ApiKey) {
    Set-Item -Path ("Env:{0}" -f $ApiKeyEnv) -Value $ApiKey
}

if (-not (Get-Item "Env:$ApiKeyEnv" -ErrorAction SilentlyContinue)) {
    throw "Missing required environment variable: $ApiKeyEnv"
}

Write-Host "Restarting real stack..." -ForegroundColor Cyan
Write-Host ("Repository: {0}" -f $repoRoot) -ForegroundColor DarkGray
Write-Host ("Bridge port: {0}" -f $BridgePort) -ForegroundColor DarkGray
Write-Host ("Web port: {0}" -f $WebPort) -ForegroundColor DarkGray

foreach ($port in @(8000, $BridgePort, $WebPort)) {
    Stop-ListeningProcess -Port $port
}

Start-Sleep -Seconds 2

$bridgeArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "start_real_bridge.ps1"),
    "-Port", "$BridgePort",
    "-UpstreamBaseUrl", $UpstreamBaseUrl,
    "-Model", $Model,
    "-ApiKeyEnv", $ApiKeyEnv
)

$webArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "start_real_web.ps1"),
    "-Port", "$WebPort",
    "-Endpoint", ("http://127.0.0.1:{0}/review" -f $BridgePort),
    "-Model", $Model,
    "-ApiKeyEnv", $ApiKeyEnv
)

$bridgeProcess = Start-Process -FilePath "powershell" -ArgumentList $bridgeArgs -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
if (-not (Wait-PortReady -Port $BridgePort)) {
    throw ("Bridge failed to listen on port {0}. Spawned PID: {1}" -f $BridgePort, $bridgeProcess.Id)
}

$webProcess = Start-Process -FilePath "powershell" -ArgumentList $webArgs -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
if (-not (Wait-PortReady -Port $WebPort)) {
    throw ("Web failed to listen on port {0}. Spawned PID: {1}" -f $WebPort, $webProcess.Id)
}

Write-Host ""
Write-Host "Real stack is ready." -ForegroundColor Green
Write-Host ("Frontend: http://127.0.0.1:{0}/" -f $WebPort) -ForegroundColor Green
Write-Host ("Ops: http://127.0.0.1:{0}/ops" -f $WebPort) -ForegroundColor Green
Write-Host ("Bridge: http://127.0.0.1:{0}/review" -f $BridgePort) -ForegroundColor Green
Write-Host ""

powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "show_stack_status.ps1")
