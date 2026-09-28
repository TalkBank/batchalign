@echo off
REM install-batchalign3.bat — One-click Batchalign installer for Windows.
REM
REM Double-click this file in Explorer to install Batchalign.
REM It installs the uv package manager (if needed) and then installs batchalign.
REM
REM After installation, open a new PowerShell or Command Prompt and type:
REM   batchalign --help
REM
REM Environment variables (for testing / internal use):
REM   BATCHALIGN_PACKAGE  Override the package spec. Can be a PyPI name (default:
REM                       "batchalign"), a local wheel path, or a PEP 508 URL.
REM   CI                  When set to "true", skips interactive prompts.

setlocal enabledelayedexpansion

if not defined BATCHALIGN_PACKAGE set "BATCHALIGN_PACKAGE=batchalign"

echo ============================================
echo   Batchalign Installer for Windows
echo ============================================
echo.

REM --------------------------------------------------------------------------
REM Step 1: Check for / install uv
REM --------------------------------------------------------------------------
where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] uv is already installed.
    goto :install_batchalign
)

echo [...]  Installing uv package manager...
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install uv.
    echo Please install uv manually from https://docs.astral.sh/uv/
    echo Then run: uv tool install batchalign
    if not "%CI%"=="true" pause
    exit /b 1
)

REM Refresh PATH so uv is available in this session.
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] uv was installed but is not on PATH yet.
    echo Close this window, open a new Command Prompt or PowerShell, and run:
    echo   uv tool install batchalign
    if not "%CI%"=="true" pause
    exit /b 1
)

echo [OK] uv installed.
echo.

REM --------------------------------------------------------------------------
REM Step 2: Install or upgrade batchalign
REM --------------------------------------------------------------------------
:install_batchalign

REM Check if batchalign is already installed.
uv tool list 2>nul | findstr /B "batchalign " >nul 2>&1
if %errorlevel% equ 0 (
    echo [...]  Upgrading batchalign...
    uv tool install --force --python 3.12 %BATCHALIGN_PACKAGE%
) else (
    echo [...]  Installing batchalign (this may take a minute)...
    uv tool install --python 3.12 %BATCHALIGN_PACKAGE%
)
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install batchalign.
    echo Please check the error messages above and try again.
    if not "%CI%"=="true" pause
    exit /b 1
)

echo.

REM --------------------------------------------------------------------------
REM Step 3: Verify
REM --------------------------------------------------------------------------
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

where batchalign >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] batchalign is installed!
    echo.
    echo ============================================
    echo   Installation complete!
    echo.
    echo   Open a NEW Command Prompt or PowerShell and run:
    echo     batchalign --help
    echo.
    echo   First-time setup (for transcription):
    echo     batchalign setup
    echo ============================================
) else (
    echo.
    echo [WARNING] batchalign installed but not found on PATH.
    echo Close this window, open a new Command Prompt or PowerShell, and try:
    echo   batchalign --help
)

echo.
if not "%CI%"=="true" pause
