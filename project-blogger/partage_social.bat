@echo off
setlocal
cd /d "%~dp0"
title Blogger Checkpoint - Social Sharing

echo ==========================================
echo   BLOGGER CHECKPOINT - SOCIAL ONLY
echo ==========================================
echo.
echo This launcher runs partage_social.py only.
echo It does NOT start blogger_app.py.
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "partage_social.py"
    goto finish
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "partage_social.py"
    goto finish
)

where python >nul 2>nul
if not errorlevel 1 (
    python "partage_social.py"
    goto finish
)

echo ERROR: Python 3 was not found.
echo Install Python 3 or create the project .venv.
set "APP_EXIT=1"
goto end

:finish
set "APP_EXIT=%ERRORLEVEL%"
echo.
if not "%APP_EXIT%"=="0" (
    echo Social sharing app stopped with an error.
) else (
    echo Social sharing app closed.
)

:end
echo.
pause
endlocal & exit /b %APP_EXIT%
