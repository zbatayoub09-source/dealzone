@echo off
setlocal
cd /d "%~dp0"
title Blogger Checkpoint Social Sharing
echo ==========================================
echo   BLOGGER CHECKPOINT - SOCIAL ONLY
echo ==========================================
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "partage_social.py"
  goto finish
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "partage_social.py"
  goto finish
)
where python >nul 2>nul
if not errorlevel 1 (
  python "partage_social.py"
  goto finish
)
echo Python 3 not found. Install Python 3 and try again.
pause
exit /b 1
:finish
echo.
if errorlevel 1 echo App stopped with an error. Check the message above.
pause
endlocal
