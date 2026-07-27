@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%.."
set "PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe"

echo Starting Comvoly locally...

if not exist "%PYTHON%" goto missing_environment
"%PYTHON%" -c "import dotenv, openai, telethon" >nul 2>&1
if errorlevel 1 goto missing_environment

start "Comvoly Sync" cmd /k ""%PYTHON%" "%SCRIPT_DIR%telegram_import.py" --watch --interval 120"
timeout /t 2 >nul
start "Comvoly Dashboard" cmd /k ""%PYTHON%" "%SCRIPT_DIR%owner_dashboard.py""
start "" http://127.0.0.1:8000
echo Comvoly opened in separate windows. Close the two Comvoly windows when you are finished.
exit /b 0

:missing_environment
echo.
echo Comvoly could not find a working local Python environment.
echo From the backend folder, run the setup steps in README.md and try again.
pause
exit /b 1
