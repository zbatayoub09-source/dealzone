@echo off
setlocal
cd /d "%~dp0"
title DealZone Facebook Page Like Helper
echo ==========================================
echo       DEALZONE PAGE LIKE HELPER
echo ==========================================
where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 goto runpy
)
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 is not installed or not in PATH.
  echo Install Python 3.10+ and select Add Python to PATH.
  pause
  exit /b 1
)
python jaime_pages.py
goto finish
:runpy
py -3 jaime_pages.py
:finish
echo.
pause
