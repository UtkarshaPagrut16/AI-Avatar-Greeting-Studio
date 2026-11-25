@echo off
REM ======================================================================
REM  AI Avatar Greeting Studio (PS 36) - one-click setup and start
REM  Double-click this file, or run it from CMD inside the project folder.
REM  It never needs administrator rights and never downloads the AI model
REM  without asking you first.
REM ======================================================================
setlocal EnableExtensions
title AI Avatar Greeting Studio
cd /d "%~dp0"

echo.
echo  ==============================================================
echo    AI Avatar Greeting Studio  -  PS 36 setup and launcher
echo  ==============================================================
echo.

REM ---------- Step 1: find Python ----------------------------------------
set "PY="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo  [FAIL] Python was not found.
    echo         Install Python 3.12 from https://www.python.org/downloads/
    echo         and tick "Add python.exe to PATH" during installation.
    echo         Then close this window and double-click run_windows.bat again.
    echo.
    pause
    exit /b 1
)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    echo  [FAIL] Your Python is older than 3.9. Please install Python 3.12.
    pause
    exit /b 1
)
echo  [ OK ] Python found:
%PY% --version

REM ---------- Step 2: virtual environment --------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  Creating a private Python environment in the .venv folder...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo  [FAIL] Could not create the virtual environment.
        echo         See docs\TROUBLESHOOTING.md, section "Virtual environment".
        pause
        exit /b 1
    )
)
set "VPY=.venv\Scripts\python.exe"
echo  [ OK ] Virtual environment ready (.venv)

REM ---------- Step 3: Python packages ------------------------------------
echo.
echo  Installing / checking Python packages (first time needs internet)...
"%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo  [WARN] pip reported a problem. If you are offline and the packages
    echo         were installed before, the app may still work. Checking...
)
"%VPY%" -c "import flask, requests" >nul 2>nul
if errorlevel 1 (
    echo  [FAIL] Flask/requests are not installed. Connect to the internet and run again.
    pause
    exit /b 1
)

REM ---------- Step 4: Ollama, model, voices (asks before downloading) -----
echo.
"%VPY%" check_setup.py --interactive
if errorlevel 1 (
    echo.
    echo  Please fix the [FAIL] items above, then run this file again.
    pause
    exit /b 1
)

REM ---------- Step 5: start the web app -----------------------------------
echo.
echo  Starting the app. Your browser will open http://127.0.0.1:5000
echo  KEEP THIS WINDOW OPEN while using the app. Press CTRL+C here to stop it.
echo.
"%VPY%" app.py --open
echo.
echo  The app has stopped. Double-click run_windows.bat to start it again.
pause
endlocal
