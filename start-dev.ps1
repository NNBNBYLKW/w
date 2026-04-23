param(
    [switch]$StartDesktop
)

$ErrorActionPreference = "Stop"

# ===============================
# 一键启动脚本（Windows / PowerShell）
# 默认启动：
#   1) apps/backend
#   2) apps/frontend
# 可选启动：
#   3) apps/desktop   （传 -StartDesktop）
#
# 使用方式：
#   - 直接双击同目录下的 start-dev.bat
#   - 或 PowerShell 中执行：
#       .\start-dev.ps1
#       .\start-dev.ps1 -StartDesktop
#
# 如果你的实际启动命令和这里不一致，只需要改下面这 3 个变量。
# ===============================

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$BackendDir  = Join-Path $RepoRoot "apps\backend"
$FrontendDir = Join-Path $RepoRoot "apps\frontend"
$DesktopDir  = Join-Path $RepoRoot "apps\desktop"

# ====== 按你的项目实际情况修改这几行 ======
$BackendCommand  = "python -m uvicorn app.main:app --reload"
$FrontendCommand = "npm run dev"
$DesktopCommand  = "npm run dev"
# ========================================

function Assert-DirExists {
    param(
        [string]$PathToCheck,
        [string]$DisplayName
    )

    if (-not (Test-Path $PathToCheck)) {
        throw "未找到 $DisplayName 目录：$PathToCheck"
    }
}

function Start-DevWindow {
    param(
        [string]$Title,
        [string]$WorkingDir,
        [string]$CommandText
    )

    $escapedDir = $WorkingDir.Replace("'", "''")
    $escapedTitle = $Title.Replace("'", "''")

    $psCommand = @"
Set-Location '$escapedDir'
`$Host.UI.RawUI.WindowTitle = '$escapedTitle'
Write-Host '==> $Title' -ForegroundColor Cyan
Write-Host '工作目录: $WorkingDir' -ForegroundColor DarkGray
Write-Host '执行命令: $CommandText' -ForegroundColor DarkGray
Write-Host ''
$CommandText
"@

    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $psCommand
    ) | Out-Null
}

Assert-DirExists -PathToCheck $BackendDir  -DisplayName "backend"
Assert-DirExists -PathToCheck $FrontendDir -DisplayName "frontend"

Write-Host "仓库根目录：$RepoRoot" -ForegroundColor Green
Write-Host "开始启动开发环境..." -ForegroundColor Green
Write-Host ""

Start-DevWindow -Title "Backend Dev"  -WorkingDir $BackendDir  -CommandText $BackendCommand
Start-DevWindow -Title "Frontend Dev" -WorkingDir $FrontendDir -CommandText $FrontendCommand

if ($StartDesktop) {
    Assert-DirExists -PathToCheck $DesktopDir -DisplayName "desktop"
    Start-DevWindow -Title "Desktop Dev" -WorkingDir $DesktopDir -CommandText $DesktopCommand
}

Write-Host "已发起启动：" -ForegroundColor Yellow
Write-Host "  - Backend" -ForegroundColor Yellow
Write-Host "  - Frontend" -ForegroundColor Yellow
if ($StartDesktop) {
    Write-Host "  - Desktop" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "提示：" -ForegroundColor Cyan
Write-Host "1. 若命令报错，请先检查各目录下依赖是否已安装（npm install / pip install 等）。"
Write-Host "2. 若你的实际启动命令不同，直接修改脚本顶部的 *_Command 变量。"
Write-Host "3. 关闭各自弹出的 PowerShell 窗口即可停止对应服务。"
