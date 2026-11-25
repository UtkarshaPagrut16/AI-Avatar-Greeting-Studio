@echo off
REM Runs the automated tests. Run run_windows.bat once first (it creates .venv).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo  Please run run_windows.bat once first to create the .venv folder.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pytest -v
pause
