@echo off
setlocal

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%backend"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\smoke_test_small_dataset.ps1" %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Small dataset smoke test failed with exit code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
