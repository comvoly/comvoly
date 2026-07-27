@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%.."
set "PROJECT_DIR=%BACKEND_DIR%\.."
set "PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe"

echo Starting Comvoly locally...

if not exist "%PYTHON%" goto missing_environment
"%PYTHON%" -c "import dotenv, openai, telethon" >nul 2>&1
if errorlevel 1 goto missing_environment

where npm.cmd >nul 2>&1
if errorlevel 1 goto missing_frontend

start "Comvoly Sync" cmd /k ""%PYTHON%" "%SCRIPT_DIR%telegram_import.py" --watch --interval 120"
timeout /t 2 >nul
start "Comvoly API" cmd /k ""%PYTHON%" "%SCRIPT_DIR%search_server.py""
if not exist "%PROJECT_DIR%\frontend\.next\BUILD_ID" goto missing_build
start "Comvoly Web" cmd /k "cd /d "%PROJECT_DIR%\frontend" && npm.cmd run start"
timeout /t 4 >nul
start "" http://localhost:3000
echo Comvoly opened in separate windows. Close the three Comvoly windows when you are finished.
exit /b 0

:missing_environment
echo.
echo Comvoly could not find a working local Python environment.
echo From the backend folder, run the setup steps in README.md and try again.
pause
exit /b 1

:missing_frontend
echo.
echo Comvoly could not find Node.js and npm for the web interface.
echo Install Node.js, then try again.
pause
exit /b 1

:missing_build
echo.
echo Comvoly needs a production web build.
echo From the frontend folder, run: npm.cmd run build
pause
exit /b 1
