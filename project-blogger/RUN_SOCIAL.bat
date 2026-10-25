@echo off
setlocal
cd /d "%~dp0"
title DealZone Social Publisher
echo ==========================================
echo       DealZone Social Publisher
echo ==========================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
  )
)
if not defined PYTHON_CMD (
  echo ERROR: Python 3.10 or newer was not found.
  echo Install Python and select "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the app's private Python environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create .venv.
    echo Make sure Python's venv component is installed.
    pause
    exit /b 1
  )
)

set "APP_PY=%~dp0.venv\Scripts\python.exe"
"%APP_PY%" -c "import googleapiclient, google.oauth2" >nul 2>nul
if errorlevel 1 (
  echo Installing YouTube API components. First run may take a few minutes...
  "%APP_PY%" -m pip install --upgrade pip
  if errorlevel 1 (
    echo ERROR: pip upgrade failed. Check your internet connection.
    pause
    exit /b 1
  )
  "%APP_PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo ERROR: Could not install requirements.txt.
    pause
    exit /b 1
  )
)

echo Starting the app...
"%APP_PY%" social_publisher.py
if errorlevel 1 (
  echo.
  echo The app stopped with an error. Take a photo of this window.
)
echo.
pause
