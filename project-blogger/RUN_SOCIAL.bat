@echo off
setlocal
cd /d "%~dp0"
title DealZone Social Publisher
echo ==========================================
echo       DealZone Social Publisher
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
  echo Using project virtual environment...
  ".venv\Scripts\python.exe" "social_publisher.py"
  goto finish
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 (
    py -3 "social_publisher.py"
    goto finish
  )
)

where python >nul 2>nul
if not errorlevel 1 (
  python --version >nul 2>nul
  if not errorlevel 1 (
    python "social_publisher.py"
    goto finish
  )
)

echo ERROR: Python 3 was not found.
echo Install Python 3, then run RUN_SOCIAL.bat again.
pause
exit /b 1

:finish
echo.
if errorlevel 1 echo The app stopped with an error. Take a photo of this window.
pause
endlocal
