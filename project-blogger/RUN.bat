@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Could not install requirements. Check Python and internet connection.
  pause
  exit /b 1
)
py -3 blogger_app.py
if errorlevel 1 (
  echo.
  echo Program stopped with an error. Read the message above.
  pause
)
