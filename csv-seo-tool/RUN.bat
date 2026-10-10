@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 seo_csv_selector.py
) else (
    python seo_csv_selector.py
)
if errorlevel 1 (
    echo.
    echo The tool stopped with an error. Check that Python 3 is installed.
    pause
)
endlocal
