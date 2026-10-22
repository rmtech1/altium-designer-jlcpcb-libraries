@echo off
rem One-click setup for the self-updating JLCPCB library for Altium Designer.
rem Double-click this file. It is safe to run again at any time.
setlocal
cd /d "%~dp0"
title JLCPCB library for Altium - setup

set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && set "PY=python"

if not defined PY (
    echo Python 3.11 or newer was not found.
    where winget >nul 2>&1
    if errorlevel 1 goto :nopython
    choice /M "Install Python 3.12 now with winget"
    if errorlevel 2 goto :nopython
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    echo.
    echo Python was installed. Close this window and double-click setup.cmd again.
    pause
    exit /b 0
)

%PY% -m jlc_altium setup %*
set "RC=%errorlevel%"
echo.
pause
exit /b %RC%

:nopython
echo.
echo Install Python 3.11+ from https://www.python.org/downloads/
echo (tick "Add python.exe to PATH"), then double-click setup.cmd again.
start "" https://www.python.org/downloads/
pause
exit /b 1
