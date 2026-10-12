@echo off
setlocal
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Install Python 3.10 or newer and enable "Add Python to PATH".
  pause
  exit /b 1
)
python app.py
pause
