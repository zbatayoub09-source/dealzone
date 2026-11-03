@echo off
setlocal
cd /d "%~dp0"
title DealZone Blogger App

echo ==========================================
echo        DEALZONE BLOGGER PUBLISHER
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher "py" was not found.
    echo Install Python 3 and try again.
    pause
    exit /b 1
)

echo Checking Python syntax...
py -3 -m py_compile blogger_app.py blogger_app_images_fixed.py
if errorlevel 1 (
    echo.
    echo ERROR: A Python syntax error was found.
    echo Check the exact file and line shown above.
    pause
    exit /b 1
)

if exist requirements.txt (
    echo.
    echo Checking required packages...
    py -3 -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo WARNING: Package installation/check failed.
        pause
        exit /b 1
    )
)

echo.
echo Starting Blogger application...
py -3 blogger_app_images_fixed.py
set "APP_EXIT=%ERRORLEVEL%"

echo.
if not "%APP_EXIT%"=="0" (
    echo Program stopped with an error. Read the message above.
) else (
    echo Blogger application closed.
)
pause
endlocal & exit /b %APP_EXIT%
