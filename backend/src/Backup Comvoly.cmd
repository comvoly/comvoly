@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "PYTHON=%SCRIPT_DIR%..\.venv\Scripts\python.exe"
set "BACKUP_SCRIPT=%SCRIPT_DIR%backup_archive.py"

if exist "%PYTHON%" (
    "%PYTHON%" --version >nul 2>&1
    if not errorlevel 1 (
        "%PYTHON%" "%BACKUP_SCRIPT%"
        goto backup_finished
    )
)

where py.exe >nul 2>&1
if not errorlevel 1 (
    py -3 "%BACKUP_SCRIPT%"
    goto backup_finished
)

where python.exe >nul 2>&1
if not errorlevel 1 (
    python "%BACKUP_SCRIPT%"
    goto backup_finished
)

echo Comvoly could not find a working Python installation.
echo Run the Comvoly setup first, then try the backup again.
pause
exit /b 1

:backup_finished
if errorlevel 1 (
    echo.
    echo The Comvoly backup was not created.
)
pause
