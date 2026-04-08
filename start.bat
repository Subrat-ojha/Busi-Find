@echo off
title Busi Find
echo Starting Busi Find...
echo.

cd /d "%~dp0"

:: Try venv flask first
if exist "Scripts\flask.exe" (
    echo Opening browser...
    start http://localhost:5000
    Scripts\flask.exe --app app run --host 0.0.0.0 --port 5000
    goto :end
)

:: Try system python
where python >nul 2>&1
if %errorlevel%==0 (
    echo Opening browser...
    start http://localhost:5000
    python -m flask --app app run --host 0.0.0.0 --port 5000
    goto :end
)

echo ERROR: Python not found. Install Python or set up the virtual environment.
pause

:end
