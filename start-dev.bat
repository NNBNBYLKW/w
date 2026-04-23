@echo off
setlocal

REM 直接双击这个文件即可启动 backend + frontend
REM 若需要连 desktop 一起启动，可把最后一行改成：
REM powershell -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1" -StartDesktop

powershell -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1" -StartDesktop

endlocal
