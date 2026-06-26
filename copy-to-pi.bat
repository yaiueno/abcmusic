@echo off
chcp 65001 >nul
if "%~1"=="" (
    echo 使い方: copy-to-pi.bat ラズパイのIP
    echo 例:     copy-to-pi.bat 192.168.0.50
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0copy-to-pi.ps1" -PiIP %1
pause
