param(
    [switch]$StartDesktop,
    [switch]$NoKillPorts,
    [switch]$SkipChecks
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "apps\backend"
$FrontendDir = Join-Path $RepoRoot "apps\frontend"
$DesktopDir = Join-Path $RepoRoot "apps\desktop"

$BackendPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$BackendUrl = "http://127.0.0.1:8000"
$FrontendUrl = "http://127.0.0.1:5173"

function Stop-Port {
    param(
        [int]$Port,
        [string]$Name
    )

    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $connections) {
        Write-Host "OK: Port $Port ($Name) is free" -ForegroundColor Green
        return
    }

    $pids = $connections |
        Select-Object -ExpandProperty OwningProcess -Unique |
        Where-Object { $_ -and $_ -gt 0 }

    foreach ($pidToStop in $pids) {
        try {
            $proc = Get-Process -Id $pidToStop -ErrorAction Stop
            Write-Host "Stopping old $Name process: PID=${pidToStop}, Process=$($proc.ProcessName)" -ForegroundColor Yellow
            Stop-Process -Id $pidToStop -Force -ErrorAction Stop
        } catch {
            Write-Host "Could not stop PID=${pidToStop}: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

function Start-DevWindow {
    param(
        [string]$Title,
        [string]$WorkingDir,
        [string]$Command
    )

    $wd = $WorkingDir.Replace("'", "''")
    $titleEscaped = $Title.Replace("'", "''")

    $script = @"
Set-Location -LiteralPath '$wd'
`$Host.UI.RawUI.WindowTitle = '$titleEscaped'
Write-Host '==> $Title' -ForegroundColor Cyan
Write-Host 'Working dir: $WorkingDir' -ForegroundColor DarkGray
Write-Host 'Command: $Command' -ForegroundColor DarkGray
Write-Host ''
$Command
"@

    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $script
    ) | Out-Null
}

function Wait-Json {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-RestMethod $Url -TimeoutSec 3
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Timeout waiting for $Url"
}

function Normalize-Path {
    param([string]$PathText)

    if (-not $PathText) {
        return ""
    }

    return [System.IO.Path]::GetFullPath($PathText).TrimEnd("\").ToLowerInvariant()
}

function Run-Checks {
    Write-Host ""
    Write-Host "Running backend checks..." -ForegroundColor Cyan

    $runtime = Wait-Json "$BackendUrl/debug/runtime" 45
    $runtimeJson = $runtime | ConvertTo-Json -Depth 8

    Write-Host ""
    Write-Host "Runtime:" -ForegroundColor Cyan
    Write-Host $runtimeJson

    $expectedPython = Normalize-Path $BackendPython
    $actualPython = Normalize-Path $runtime.sys_executable

    if ($actualPython -eq $expectedPython) {
        Write-Host "OK: backend uses .venv Python" -ForegroundColor Green
    } else {
        Write-Host "WARNING: backend Python mismatch" -ForegroundColor Red
        Write-Host "Expected: $BackendPython"
        Write-Host "Actual:   $($runtime.sys_executable)"
    }

    if ($runtime.PSObject.Properties.Name -contains "process_id") {
        Write-Host "OK: process_id = $($runtime.process_id)" -ForegroundColor Green
    } else {
        Write-Host "WARNING: process_id missing. Backend may be old code." -ForegroundColor Red
    }

    if ($runtime.PSObject.Properties.Name -contains "process_start_time") {
        Write-Host "OK: process_start_time = $($runtime.process_start_time)" -ForegroundColor Green
    } else {
        Write-Host "WARNING: process_start_time missing. Backend may be old code." -ForegroundColor Red
    }

    $warmup = Wait-Json "$BackendUrl/debug/thumbnails/warmup" 20
    $warmupJson = $warmup | ConvertTo-Json -Depth 8

    Write-Host ""
    Write-Host "Thumbnail warmup:" -ForegroundColor Cyan
    Write-Host $warmupJson

    if ($warmupJson -match "subprocess-v1") {
        Write-Host "OK: PDF thumbnail render mode is subprocess-v1" -ForegroundColor Green
    } else {
        Write-Host "WARNING: pdf_render_mode=subprocess-v1 missing. Backend may be old code." -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Checks done." -ForegroundColor Cyan
}

if (-not (Test-Path $BackendDir)) {
    throw "Backend dir not found: $BackendDir"
}

if (-not (Test-Path $FrontendDir)) {
    throw "Frontend dir not found: $FrontendDir"
}

if (-not (Test-Path $BackendPython)) {
    throw "Backend Python not found: $BackendPython"
}

$pythonVersion = & $BackendPython --version

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Workbench dev startup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Repo root:       $RepoRoot"
Write-Host "Backend dir:     $BackendDir"
Write-Host "Frontend dir:    $FrontendDir"
Write-Host "Backend Python:  $BackendPython"
Write-Host "Python version:  $pythonVersion"
Write-Host ""

if (-not $NoKillPorts) {
    Write-Host "Cleaning old ports..." -ForegroundColor Cyan
    Stop-Port -Port 8000 -Name "Backend"
    Stop-Port -Port 5173 -Name "Frontend"
    Write-Host ""
}

$BackendCommand = "& '$BackendPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
$FrontendCommand = "npm run dev -- --host 127.0.0.1 --port 5173"
$DesktopCommand = "npm run dev"

Write-Host "Starting backend..." -ForegroundColor Green
Start-DevWindow -Title "Backend Dev" -WorkingDir $BackendDir -Command $BackendCommand

Write-Host "Starting frontend..." -ForegroundColor Green
Start-DevWindow -Title "Frontend Dev" -WorkingDir $FrontendDir -Command $FrontendCommand

if ($StartDesktop) {
    if (-not (Test-Path $DesktopDir)) {
        throw "Desktop dir not found: $DesktopDir"
    }

    Write-Host "Starting desktop..." -ForegroundColor Green
    Start-DevWindow -Title "Desktop Dev" -WorkingDir $DesktopDir -Command $DesktopCommand
}

Write-Host ""
Write-Host "Started:" -ForegroundColor Yellow
Write-Host "Backend:  $BackendUrl"
Write-Host "Frontend: $FrontendUrl"
if ($StartDesktop) {
    Write-Host "Desktop:  started"
}

if (-not $SkipChecks) {
    try {
        Run-Checks
    } catch {
        Write-Host ""
        Write-Host "Post-start checks failed:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Write-Host "Check the Backend Dev window." -ForegroundColor Yellow
    }
}