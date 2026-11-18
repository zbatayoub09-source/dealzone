@echo off
setlocal
cd /d "%~dp0"
title Facebook Comment Publisher
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Python 3 is required. Install Python with Tkinter, then run again.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check requests
if errorlevel 1 (
    echo Could not install required package: requests
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
endlocal
