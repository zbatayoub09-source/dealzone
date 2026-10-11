@echo off
setlocal
cd /d "%~dp0"
title DealZone Social Publisher
echo ==========================================
echo       DealZone Social Publisher
echo ==========================================
echo.
echo Checking Python...
where py
if not errorlevel 1 (
  py -3 --version
  if not errorlevel 1 (
    py -3 social_publisher.py
    goto :finish
  )
)
where python
if not errorlevel 1 (
  python --version
  if not errorlevel 1 (
    python social_publisher.py
    goto :finish
  )
)
echo.
echo ERROR: Python was not found or could not start.
echo Install Python 3.10 or newer and tick "Add Python to PATH".
echo If Python is installed, send a photo of this window.
:finish
echo.
echo If the app did not open, copy or photograph the error above.
pause
