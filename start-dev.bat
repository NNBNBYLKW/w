@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo Workbench dev startup
echo Current dir: %CD%
echo Mode: Backend + Frontend + Desktop
echo ==========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0start-dev.ps1" -StartDesktop

endlocal