@echo off
setlocal enabledelayedexpansion

:: Sakura AI - Start Script
:: Handles uv installation, Python 3.12 setup, venv creation, and launch

title Sakura AI Launcher
color 0A

echo.
echo  ========================================
echo   🌸 Sakura AI - Launcher
echo  ========================================
echo.


:: Check if uv is installed

:main_flow
:: Check if uv is installed
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] uv not found. Installing uv...
    echo.
    
    :: Try winget first (cleanest method)
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Installing uv via winget...
        winget install --id=astral-sh.uv -e --silent
        if !errorlevel! equ 0 (
            echo [OK] uv installed via winget
            :: Refresh PATH
            call refreshenv >nul 2>&1
        ) else (
            goto :install_uv_powershell
        )
    ) else (
        goto :install_uv_powershell
    )
) else (
    echo [OK] uv is installed
)

goto :check_uv

:install_uv_powershell
echo [INFO] Installing uv via PowerShell installer...
powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install uv
    echo [INFO] Please install uv manually: https://docs.astral.sh/uv/
    pause
    exit /b 1
)
echo [OK] uv installed via PowerShell

:: Add uv to current session PATH
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

:check_uv
:: Verify uv is now available
where uv >nul 2>&1
if %errorlevel% neq 0 (
    :: Try common install locations
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    ) else if exist "%LOCALAPPDATA%\uv\uv.exe" (
        set "PATH=%LOCALAPPDATA%\uv;%PATH%"
    ) else (
        echo [ERROR] uv not found in PATH after installation
        echo [INFO] Please restart your terminal or add uv to PATH manually
        pause
        exit /b 1
    )
)

echo.

:: Check for Python 3.12
echo [INFO] Checking Python version...

:: Detect which venv folder exists (.venv or venv)
set VENV_DIR=
if exist ".venv\Scripts\python.exe" (
    set VENV_DIR=.venv
) else if exist "venv\Scripts\python.exe" (
    set VENV_DIR=venv
)

:: Check existing venv has correct Python
if defined VENV_DIR (
    for /f "tokens=2 delims= " %%v in ('"!VENV_DIR!\Scripts\python.exe" --version 2^>^&1') do set VENV_PY_VER=%%v
    echo [INFO] Found !VENV_DIR! with Python !VENV_PY_VER!
    
    :: Check if it's 3.12.x
    echo !VENV_PY_VER! | findstr /b "3.12" >nul
    if !errorlevel! equ 0 (
        echo [OK] !VENV_DIR! has Python 3.12
        goto :install_deps
    ) else (
        echo [WARN] !VENV_DIR! has wrong Python version, recreating...
        rmdir /s /q !VENV_DIR! 2>nul
        set VENV_DIR=
    )
) else (
    echo [INFO] No existing virtual environment found
)

:: Check system Python
set SYSTEM_PY_OK=0
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set SYS_PY_VER=%%v
    echo [INFO] System Python: !SYS_PY_VER!
    echo !SYS_PY_VER! | findstr /b "3.12" >nul
    if !errorlevel! equ 0 (
        set SYSTEM_PY_OK=1
        echo [OK] System Python is 3.12
    )
)

:: Install Python 3.12 via uv if needed
if !SYSTEM_PY_OK! equ 0 (
    echo [INFO] Installing Python 3.12 via uv...
    uv python install 3.12
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install Python 3.12
        pause
        exit /b 1
    )
    echo [OK] Python 3.12 installed via uv
)

echo.

:: Create virtual environment if none exists
if not defined VENV_DIR (
    set VENV_DIR=.venv
    echo [INFO] Creating virtual environment with Python 3.12...
    uv venv --python 3.12 .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

:install_deps
:: Check if requirements need to be installed
echo.
echo [INFO] Checking dependencies...

:: Use uv pip for fast dependency installation
if exist "requirements.txt" (
    echo [INFO] Installing/updating dependencies via uv...
    !VENV_DIR!\Scripts\python.exe -m pip show google-genai >nul 2>&1
    if !errorlevel! neq 0 (
        uv pip install -r requirements.txt --python !VENV_DIR!\Scripts\python.exe
        if !errorlevel! neq 0 (
            echo [WARN] uv pip failed, trying regular pip...
            !VENV_DIR!\Scripts\pip.exe install -r requirements.txt
        )
        echo [OK] Dependencies installed
    ) else (
        echo [OK] Dependencies already installed
    )
) else (
    echo [WARN] requirements.txt not found
)

echo.

:: Check for .env file
if not exist ".env" (
    if exist ".env.example" (
        echo [WARN] .env file not found!
        echo [INFO] Please copy .env.example to .env and configure your API keys
        echo.
        copy .env.example .env >nul
        echo [INFO] Created .env from .env.example - please edit it with your keys
        notepad .env
        echo.
        echo Press any key after configuring .env...
        pause >nul
    ) else (
        echo [WARN] No .env or .env.example found
        echo [INFO] Create a .env file with at least GEMINI_API_KEY=your_key
    )
)

:: Final Python version check
echo.
echo [INFO] Environment ready:
!VENV_DIR!\Scripts\python.exe --version
echo.

:: Present launch menu (now that venv is ready)
:run_menu
echo.
echo =============================
echo Ready to launch. Choose mode:
echo  1) Run as current user (normal)
echo  2) Run as Admin (UAC) - only launches the app elevated
echo  Q) Quit
set /p launchChoice=Enter choice [1/2/Q]: 
if /i "%launchChoice%"=="1" goto launch_normal
if /i "%launchChoice%"=="2" goto launch_admin
if /i "%launchChoice%"=="Q" goto :eof
echo Invalid choice.
goto run_menu

:launch_normal
echo  ========================================
echo   🌸 Starting Sakura AI (normal user)
echo  ========================================
echo.
:: Launch detached in a new window and exit launcher
start "" "%CD%\%VENV_DIR%\Scripts\python.exe" "%CD%\main.py"
goto :eof

:launch_admin
echo  ========================================
echo   🌸 Starting Sakura AI (elevated)
echo  ========================================
echo.
:: Build absolute paths and helper file names
set "REPO=%CD%"
set "PYEX=%REPO%\%VENV_DIR%\Scripts\python.exe"
set "MAINPY=%REPO%\main.py"
set "ADMIN_BATCH=%temp%\sakura_admin_run.bat"
set "ADMIN_VBS=%temp%\sakura_admin_run.vbs"

> "%ADMIN_BATCH%" echo @echo off
>> "%ADMIN_BATCH%" echo cd /d "%REPO%"
>> "%ADMIN_BATCH%" echo %SystemRoot%\System32\rundll32.exe shell32.dll,SHCreateLocalServerRunDll {c82192ee-6cb5-4bc0-9ef0-fb818773790a}
>> "%ADMIN_BATCH%" echo MD "%%USERPROFILE%%\AppData\Local\Temp\AIO" 2^>nul
>> "%ADMIN_BATCH%" echo echo. ^> "%%USERPROFILE%%\AppData\Local\Temp\AIO\log.txt"
>> "%ADMIN_BATCH%" echo "%PYEX%" "%MAINPY%"
>> "%ADMIN_BATCH%" echo exit

> "%ADMIN_VBS%" echo Set UAC = CreateObject("Shell.Application")
>> "%ADMIN_VBS%" echo UAC.ShellExecute "%ADMIN_BATCH%", "", "", "runas", 1

:: Invoke the VBScript to launch the admin batch elevated
cscript //nologo "%ADMIN_VBS%"

:: Give the elevated proc a moment to start, then remove temp files (best-effort)
timeout /t 3 >nul
del "%ADMIN_VBS%" 2>nul
del "%ADMIN_BATCH%" 2>nul

goto :eof

:after_run
echo.
echo [INFO] Sakura has stopped.
goto :eof
