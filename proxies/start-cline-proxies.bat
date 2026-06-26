@echo off
REM Start both Cline proxies (11435=fast, 11436=think) at logon
powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0switch-cline-mode.ps1" -Mode start
