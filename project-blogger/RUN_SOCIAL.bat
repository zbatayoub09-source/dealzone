@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo       DealZone Social Publisher
echo ==========================================
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 social_publisher.py
) else (
  python social_publisher.py
)
if errorlevel 1 (
  echo.
  echo App stopped with an error. Check Python installation.
  pause
)
