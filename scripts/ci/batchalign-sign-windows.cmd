@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0sign-windows-artifact.ps1" "%~1"
exit /b %ERRORLEVEL%
