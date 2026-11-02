@echo off
setlocal
cd /d "%~dp0"
title Blogger Checkpoint - Social Sharing
echo ==========================================
echo     BLOGGER CHECKPOINT SOCIAL SHARING
echo ==========================================
echo.
echo This launcher opens Blogger app.
echo Connect Blogger, choose Facebook / Instagram / Threads,
echo then click: SHARE ALL POSTS FROM BLOGGER CHECKPOINT
echo.

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "blogger_app.py"
  goto finish
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 "blogger_app.py"
  goto finish
)

where python >nul 2>nul
if not errorlevel 1 (
  python "blogger_app.py"
  goto finish
)

echo ERROR: Python 3 was not found.
pause
exit /b 1

:finish
echo.
if errorlevel 1 echo The app stopped with an error. Check the message above.
pause
endlocal
