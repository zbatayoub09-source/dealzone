@echo off
setlocal
cd /d "%~dp0"
title DealZone Social Publisher
echo ==========================================
echo       DealZone Social Publisher
echo ==========================================
echo.

set "APP_PY="
if exist ".venv\Scripts\python.exe" (
  set "APP_PY=%~dp0.venv\Scripts\python.exe"
  goto run_app
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 (
    set "APP_PY=py -3"
    goto run_app
  )
)

where python >nul 2>nul
if not errorlevel 1 (
  python --version >nul 2>nul
  if not errorlevel 1 (
    set "APP_PY=python"
    goto run_app
  )
)

echo ERROR: Python 3 was not found.
echo Install Python 3, then run RUN_SOCIAL.bat again.
pause
exit /b 1

:run_app
echo Starting DealZone Social Publisher...
%APP_PY% "social_publisher.py"
if errorlevel 1 (
  echo.
  echo The app stopped with an error. Take a photo of this window.
)
echo.
pause
endlocal
