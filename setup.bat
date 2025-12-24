@echo off
setlocal enabledelayedexpansion

:: Sakura AI - Setup Script
:: First-time setup: installs uv, Python 3.12, creates venv, installs deps

title Sakura AI Setup
color 0E

echo.
echo  ========================================
echo   🌸 Sakura AI - First Time Setup
echo  ========================================
echo.
echo This script will:
echo   1. Install uv (fast Python package manager)
echo   2. Install Python 3.12 via uv
echo   3. Create virtual environment
echo   4. Install all dependencies
echo   5. Create .env configuration file
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul
echo.

:: ============================================
:: STEP 1: Install uv
:: ============================================
echo [STEP 1/5] Installing uv...
echo.

where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] uv is already installed
    uv --version
) else (
    :: Try winget first
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Installing uv via winget...
        winget install --id=astral-sh.uv -e --accept-source-agreements --accept-package-agreements
        if !errorlevel! equ 0 (
            echo [OK] uv installed via winget
        ) else (
            goto :uv_powershell
        )
    ) else (
        goto :uv_powershell
    )
    goto :uv_done
    
    :uv_powershell
    echo [INFO] Installing uv via PowerShell...
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install uv
        echo.
        echo Please install uv manually:
        echo   - Via winget: winget install astral-sh.uv
        echo   - Via pip: pip install uv
        echo   - Via installer: https://docs.astral.sh/uv/
        pause
        exit /b 1
    )
    echo [OK] uv installed
    
    :uv_done
    :: Add to PATH for current session
    set "PATH=%USERPROFILE%\.local\bin;%LOCALAPPDATA%\uv;%PATH%"
)

echo.

:: ============================================
:: STEP 2: Install Python 3.12
:: ============================================
echo [STEP 2/5] Installing Python 3.12...
echo.

:: Check if Python 3.12 is available via uv
uv python list 2>nul | findstr "3.12" >nul
if %errorlevel% equ 0 (
    echo [OK] Python 3.12 is available
) else (
    echo [INFO] Downloading Python 3.12 via uv...
    uv python install 3.12
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install Python 3.12
        pause
        exit /b 1
    )
    echo [OK] Python 3.12 installed
)

echo.

:: ============================================
:: STEP 3: Create Virtual Environment
:: ============================================
echo [STEP 3/5] Creating virtual environment...
echo.

if exist ".venv" (
    echo [INFO] Removing existing .venv...
    rmdir /s /q .venv
)

uv venv --python 3.12 .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

:: Verify Python version in venv
for /f "tokens=2 delims= " %%v in ('".venv\Scripts\python.exe" --version 2^>^&1') do set PY_VER=%%v
echo [OK] Virtual environment created with Python !PY_VER!

echo.

:: ============================================
:: STEP 4: Install Dependencies
:: ============================================
echo [STEP 4/5] Installing dependencies...
echo.

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found!
    pause
    exit /b 1
)

echo [INFO] Installing packages via uv pip (this may take a minute)...
uv pip install -r requirements.txt --python .venv\Scripts\python.exe
if %errorlevel% neq 0 (
    echo [WARN] uv pip had issues, trying standard pip...
    .venv\Scripts\pip.exe install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo [OK] Dependencies installed

echo.

:: ============================================
:: STEP 5: Configure .env
:: ============================================
echo [STEP 5/5] Configuring environment...
echo.

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] Created .env from .env.example
    ) else (
        echo [INFO] Creating basic .env file...
        (
            echo # Sakura AI Configuration
            echo.
            echo # Required - Gemini API Key
            echo GEMINI_API_KEY=your_api_key_here
            echo.
            echo # Optional - Backup API keys
            echo # GEMINI_API_KEY_2=backup_key
            echo.
            echo # Assistant Settings
            echo ASSISTANT_NAME=Sakura
            echo SAKURA_PERSONALITY=friendly
            echo VOICE_NAME=Aoede
            echo.
            echo # Wake Word (optional^)
            echo # PICOVOICE_ACCESS_KEY=your_key
            echo # WAKE_WORD_KEYWORDS=jarvis
        ) > .env
        echo [OK] Created .env file
    )
    
    echo.
    echo [IMPORTANT] Please edit .env with your API keys!
    echo Opening .env in notepad...
    notepad .env
) else (
    echo [OK] .env already exists
)

echo.

:: ============================================
:: Setup Complete
:: ============================================
echo  ========================================
echo   🌸 Setup Complete!
echo  ========================================
echo.
echo Summary:
echo   - uv: installed
echo   - Python: !PY_VER!
echo   - Virtual environment: .venv
echo   - Dependencies: installed
echo   - Configuration: .env
echo.
echo To start Sakura:
echo   - Double-click start.bat
echo   - Or run: .venv\Scripts\python.exe main.py
echo.
echo [NOTE] uv is required for MCP server tools (uvx command)
echo.

set /p LAUNCH="Launch Sakura now? (Y/N): "
if /i "!LAUNCH!"=="Y" (
    echo.
    echo Starting Sakura...
    .venv\Scripts\python.exe main.py
)

pause
