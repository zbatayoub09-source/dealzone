@echo off
setlocal
cd /d "%~dp0"
title Facebook Page Creator
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 page_creator.py
) else (
    python page_creator.py
)
if errorlevel 1 (
    echo.
    echo Could not start the app. Install Python 3 with Tkinter.
    pause
)
endlocal
