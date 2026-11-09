@echo off
setlocal
cd /d "%~dp0"
title DealZone Manager
echo ==========================================
echo          DEALZONE MANAGER
echo ==========================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment...
  where py >nul 2>nul
  if not errorlevel 1 (py -3 -m venv .venv) else (python -m venv .venv)
  if errorlevel 1 goto :error
)
echo Checking Flask...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
echo.
echo Starting DealZone Manager...
".venv\Scripts\python.exe" app.py
goto :end
:error
echo.
echo ERROR: Python setup failed. Install Python 3 and try again.
pause
:end
