@echo off
setlocal
cd /d "%~dp0"
title DealZone Sheets Publisher
if not exist .venv (
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Could not create virtual environment. Install Python first.
    pause
    exit /b 1
  )
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env (
  copy .env.example .env
  echo.
  echo Created .env. Edit it and add your Google Sheets ID and Facebook Page Access Token.
  echo Also put your Google service-account file here as credentials.json.
  notepad .env
  pause
  exit /b 0
)
python app.py
pause
